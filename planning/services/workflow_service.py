from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone as django_timezone

from accounts.models import AdvisorAssignment, Role
from accounts.permissions import get_user_roles_for_institution
from institutions.models import Institution
from planning.models import (
    OverrideEvent,
    Plan,
    PlanAuditLog,
    PlanReviewDecision,
    PlanStatus,
    PlanVersion,
    ReviewAction,
)
from planning.services.plan_management_service import PlanConcurrencyError


class WorkflowTransitionError(ValidationError):
    """Raised when an invalid state machine transition is attempted."""
    pass


ALLOWED_TRANSITIONS: dict[str, dict[str, str]] = {
    PlanStatus.DRAFT: {
        "submit": PlanStatus.SUBMITTED,
    },
    PlanStatus.SUBMITTED: {
        "start_review": PlanStatus.UNDER_REVIEW,
        "supersede": PlanStatus.SUPERSEDED,
    },
    PlanStatus.UNDER_REVIEW: {
        "approve": PlanStatus.APPROVED,
        "return": PlanStatus.RETURNED,
        "reject": PlanStatus.REJECTED,
        "supersede": PlanStatus.SUPERSEDED,
    },
    PlanStatus.RETURNED: {
        "resubmit": PlanStatus.RESUBMITTED,
        "supersede": PlanStatus.SUPERSEDED,
    },
    PlanStatus.RESUBMITTED: {
        "start_review": PlanStatus.UNDER_REVIEW,
        "supersede": PlanStatus.SUPERSEDED,
    },
    PlanStatus.REJECTED: {
        "supersede": PlanStatus.SUPERSEDED,
    },
    PlanStatus.APPROVED: {
        "supersede": PlanStatus.SUPERSEDED,
    },
}


def check_advisor_can_review(
    actor: User,
    plan: Plan,
) -> None:
    """
    Verifies that the actor is authorized to review the plan.
    - User must have active membership in the plan's institution.
    - User must possess ADVISOR, COORDINATOR, or ADMIN role.
    - If ADVISOR (and not Coordinator/Admin), must have an active AdvisorAssignment to the student.
    - Students are never authorized to review/approve plans.
    """
    inst = plan.institution
    roles = get_user_roles_for_institution(actor, inst)

    if not roles:
        raise PermissionDenied("User does not belong to this institution.")

    if Role.STUDENT in roles and len(roles) == 1:
        raise PermissionDenied("Students are not permitted to approve or review plans.")

    # Admins and coordinators have institution-wide authority
    if Role.ADMIN in roles or Role.COORDINATOR in roles:
        return

    if Role.ADVISOR in roles:
        student_user = plan.student_record.student
        is_assigned = AdvisorAssignment.objects.filter(
            institution=inst,
            advisor__user=actor,
            student__user=student_user,
            is_active=True,
        ).exists()

        if not is_assigned:
            raise PermissionDenied(
                f"Advisor {actor.username} is not assigned to student {student_user.username}."
            )
        return

    raise PermissionDenied("User does not have an academic advising role.")


def transition_plan_version(
    plan: Plan,
    version: PlanVersion,
    action: str,
    actor: User,
    comments: str = "",
    expected_row_version: int | None = None,
    idempotency_key: str | None = None,
) -> PlanReviewDecision:
    """
    Executes a formal state machine transition on a plan and its specific version.
    Runs inside a select_for_update transaction to prevent race conditions and enforce OCC.
    """
    # 1. Idempotency Check
    if idempotency_key:
        existing_decision = PlanReviewDecision.objects.filter(
            idempotency_key=idempotency_key
        ).first()
        if existing_decision:
            return existing_decision

    with transaction.atomic():
        # Lock plan and version rows
        locked_plan = Plan.objects.select_for_update().get(id=plan.id)
        locked_version = PlanVersion.objects.select_for_update().get(id=version.id)

        # 2. Check optimistic concurrency control
        if expected_row_version is not None and locked_plan.row_version != expected_row_version:
            raise PlanConcurrencyError(
                f"Plan was modified by another session (current row_version: {locked_plan.row_version}, expected: {expected_row_version})."
            )

        # 3. Enforce role authorization first (deny unauthorized actors immediately)
        check_advisor_can_review(actor, locked_plan)

        # 4. Check allowed transition from state machine table
        current_status = locked_version.status
        allowed_actions = ALLOWED_TRANSITIONS.get(current_status, {})

        if action not in allowed_actions:
            raise WorkflowTransitionError(
                f"Invalid workflow transition: Cannot '{action}' from status '{current_status}'. "
                f"Allowed actions: {list(allowed_actions.keys())}."
            )

        target_status = allowed_actions[action]

        # 5. Comment requirement for return or reject
        if action in ["return", "reject"] and (not comments or not comments.strip()):
            raise WorkflowTransitionError(
                f"Comments detailing the reasons for {action} are required for student revision."
            )

        # 6. Apply status transition to version and plan
        from_status = locked_version.status
        locked_version.status = target_status
        # Use super().save on PlanVersion to bypass immutability check for status updates
        super(PlanVersion, locked_version).save(update_fields=["status"])

        locked_plan.status = target_status
        locked_plan.row_version += 1
        locked_plan.save(update_fields=["status", "row_version", "updated_at"])

        # 7. Record Review Decision
        review_action_enum = {
            "start_review": ReviewAction.START_REVIEW,
            "approve": ReviewAction.APPROVE,
            "return": ReviewAction.RETURN,
            "reject": ReviewAction.REJECT,
        }.get(action, ReviewAction.APPROVE)

        decision = PlanReviewDecision.objects.create(
            institution=locked_plan.institution,
            plan=locked_plan,
            plan_version=locked_version,
            reviewer=actor,
            action=review_action_enum,
            from_status=from_status,
            to_status=target_status,
            comments=comments,
            idempotency_key=idempotency_key,
        )

        # 8. Append to Audit Log
        PlanAuditLog.objects.create(
            institution=locked_plan.institution,
            plan=locked_plan,
            plan_version=locked_version,
            actor=actor,
            action=f"PLAN_{action.upper()}",
            from_status=from_status,
            to_status=target_status,
            comment=comments,
            metadata={
                "version_number": locked_version.version_number,
                "row_version": locked_plan.row_version,
                "idempotency_key": idempotency_key,
            },
        )

        # 9. Trigger In-App Notification (Idempotent)
        try:
            from notifications.services import notify_plan_review_decision

            notify_plan_review_decision(
                plan=locked_plan,
                decision_action=decision.action,
                reviewer=actor,
            )
        except Exception:
            pass

        return decision


def start_review(
    plan: Plan,
    version: PlanVersion,
    advisor: User,
    expected_row_version: int | None = None,
    idempotency_key: str | None = None,
) -> PlanReviewDecision:
    return transition_plan_version(
        plan=plan,
        version=version,
        action="start_review",
        actor=advisor,
        comments="Advisor initiated official review.",
        expected_row_version=expected_row_version,
        idempotency_key=idempotency_key,
    )


def approve_plan_version(
    plan: Plan,
    version: PlanVersion,
    advisor: User,
    comments: str = "",
    expected_row_version: int | None = None,
    idempotency_key: str | None = None,
) -> PlanReviewDecision:
    return transition_plan_version(
        plan=plan,
        version=version,
        action="approve",
        actor=advisor,
        comments=comments or "Approved as scheduled.",
        expected_row_version=expected_row_version,
        idempotency_key=idempotency_key,
    )


def return_plan_version(
    plan: Plan,
    version: PlanVersion,
    advisor: User,
    comments: str,
    expected_row_version: int | None = None,
    idempotency_key: str | None = None,
) -> PlanReviewDecision:
    return transition_plan_version(
        plan=plan,
        version=version,
        action="return",
        actor=advisor,
        comments=comments,
        expected_row_version=expected_row_version,
        idempotency_key=idempotency_key,
    )


def reject_plan_version(
    plan: Plan,
    version: PlanVersion,
    advisor: User,
    comments: str,
    expected_row_version: int | None = None,
    idempotency_key: str | None = None,
) -> PlanReviewDecision:
    return transition_plan_version(
        plan=plan,
        version=version,
        action="reject",
        actor=advisor,
        comments=comments,
        expected_row_version=expected_row_version,
        idempotency_key=idempotency_key,
    )


def record_plan_override(
    plan: Plan,
    version: PlanVersion,
    actor: User,
    override_type: str,
    justification: str,
    metadata: dict[str, Any] | None = None,
) -> OverrideEvent:
    """
    Records an authoritative override on a degree plan version.
    - Requires advisor/coordinator/admin role authorization.
    - Requires non-empty justification of at least 15 characters.
    - Resulting OverrideEvent is strictly immutable (append-only).
    - NEVER modifies official StudentRecord or TranscriptEntry data.
    """
    check_advisor_can_review(actor, plan)

    if not justification or len(justification.strip()) < 15:
        raise ValidationError(
            "An academic override requires a non-empty justification of at least 15 characters."
        )

    with transaction.atomic():
        override = OverrideEvent.objects.create(
            institution=plan.institution,
            plan=plan,
            plan_version=version,
            actor=actor,
            override_type=override_type,
            justification=justification.strip(),
            metadata=metadata or {},
        )

        PlanAuditLog.objects.create(
            institution=plan.institution,
            plan=plan,
            plan_version=version,
            actor=actor,
            action="RECORD_OVERRIDE",
            from_status=version.status,
            to_status=version.status,
            comment=f"Override: {override_type}. Justification: {justification.strip()}",
            metadata={
                "override_id": str(override.id),
                "override_type": override_type,
            },
        )

        return override


def get_advisor_review_queue(
    user: User,
    institution: Institution,
    status_filter: str | None = None,
    programme_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Fetches the review queue for an advisor or coordinator within an institution.
    - Advisors see assigned advisees.
    - Coordinators and Admins see all plans in the institution.
    - Includes waiting age, programme details, latest version snapshot, and risk summary.
    """
    roles = get_user_roles_for_institution(user, institution)

    base_plans = (
        Plan.objects.filter(institution=institution)
        .select_related(
            "student_record__student",
            "student_record__programme",
            "curriculum_version",
        )
        .prefetch_related("versions", "override_events")
    )

    if Role.ADMIN not in roles and Role.COORDINATOR not in roles:
        if Role.ADVISOR not in roles:
            return []
        assigned_student_ids = AdvisorAssignment.objects.filter(
            institution=institution,
            advisor__user=user,
            is_active=True,
        ).values_list("student__user_id", flat=True)

        base_plans = base_plans.filter(student_record__student_id__in=assigned_student_ids)

    if status_filter and status_filter.upper() != "ALL":
        base_plans = base_plans.filter(status=status_filter.upper())
    else:
        # Default queue excludes archived drafts
        base_plans = base_plans.exclude(status=PlanStatus.ARCHIVED)

    if programme_filter:
        base_plans = base_plans.filter(student_record__programme__code=programme_filter)

    queue: list[dict[str, Any]] = []
    now = django_timezone.now()

    for p in base_plans.order_by("-updated_at"):
        latest_version = p.versions.order_by("-version_number").first()
        student = p.student_record.student

        submitted_at = latest_version.submitted_at if latest_version else p.created_at
        age_days = (now - submitted_at).days

        override_count = p.override_events.count()

        # Check simulation status from frozen snapshot
        sim_data = latest_version.snapshot_data.get("simulation", {}) if latest_version else {}
        hard_count = len(sim_data.get("hard_constraints", []))
        warning_count = len(sim_data.get("warnings", []))

        queue.append({
            "plan_id": str(p.id),
            "plan_name": p.name,
            "status": p.status,
            "row_version": p.row_version,
            "student_id": str(p.student_record.id),
            "student_username": student.username,
            "student_email": student.email,
            "programme_code": p.student_record.programme.code,
            "programme_name": p.student_record.programme.name,
            "latest_version_id": str(latest_version.id) if latest_version else None,
            "latest_version_number": latest_version.version_number if latest_version else 1,
            "latest_version_status": latest_version.status if latest_version else p.status,
            "submitted_at": submitted_at.isoformat(),
            "waiting_days": max(0, age_days),
            "override_count": override_count,
            "hard_constraints_count": hard_count,
            "warnings_count": warning_count,
            "is_valid_for_submission": sim_data.get("is_valid_for_submission", True),
            "projected_graduation_term": sim_data.get("projected_graduation_term"),
        })

    return queue
