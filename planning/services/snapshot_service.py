import json
from typing import Any

from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import F, Max

from planning.models import Plan, PlanStatus, PlanVersion, PlanVersionStatus
from planning.services.plan_management_service import PlanValidationError
from planning.services.simulation_service import simulate_plan


def create_plan_version_snapshot(
    plan: Plan,
    submitted_by: User,
    submission_note: str = "",
) -> PlanVersion:
    """
    Validates, simulates, and freezes the plan into an immutable PlanVersion snapshot.
    Transitions plan status to SUBMITTED.
    """
    # 1. Run simulation to verify no hard constraints block submission
    simulation_report = simulate_plan(plan)
    if not simulation_report.is_valid_for_submission:
        blocking = [c.message for c in simulation_report.hard_constraints]
        raise PlanValidationError(
            f"Cannot submit plan with unresolved hard constraints: {'; '.join(blocking)}"
        )

    # 2. Serialize current plan items into a frozen structure
    items = plan.items.select_related("course", "planned_term").order_by(
        "term_index", "position"
    )
    items_snapshot = [
        {
            "course_id": str(it.course.id),
            "course_code": it.course.code,
            "course_title": it.course.title,
            "credits": str(it.course.credits),
            "term_id": str(it.planned_term.id),
            "term_code": it.planned_term.code,
            "term_index": it.term_index,
            "position": it.position,
            "notes": it.notes,
        }
        for it in items
    ]

    snapshot_payload: dict[str, Any] = {
        "plan_id": str(plan.id),
        "plan_name": plan.name,
        "curriculum_version_id": str(plan.curriculum_version.id),
        "curriculum_version_number": plan.curriculum_version.version_number,
        "items": items_snapshot,
        "simulation": simulation_report.to_dict(),
        "submitted_by_username": submitted_by.username,
        "submission_note": submission_note,
    }

    clean_snapshot = json.loads(json.dumps(snapshot_payload, cls=DjangoJSONEncoder))

    with transaction.atomic():
        max_ver = PlanVersion.objects.filter(plan=plan).aggregate(
            Max("version_number")
        )["version_number__max"]
        next_version = (max_ver or 0) + 1

        version = PlanVersion.objects.create(
            institution=plan.institution,
            plan=plan,
            version_number=next_version,
            snapshot_data=clean_snapshot,
            status=PlanVersionStatus.SUBMITTED,
            submitted_by=submitted_by,
            submission_note=submission_note,
        )

        plan.status = PlanStatus.SUBMITTED
        Plan.objects.filter(id=plan.id).update(
            status=PlanStatus.SUBMITTED,
            row_version=F("row_version") + 1,
        )
        plan.refresh_from_db()
        return version


def compare_plan_versions(
    version_a: PlanVersion,
    version_b: PlanVersion,
) -> dict[str, Any]:
    """
    Compares two frozen PlanVersion snapshots and outputs differences in course assignments,
    term schedules, and simulation metrics.
    """
    items_a = {it["course_code"]: it for it in version_a.snapshot_data.get("items", [])}
    items_b = {it["course_code"]: it for it in version_b.snapshot_data.get("items", [])}

    added_courses = [it for code, it in items_b.items() if code not in items_a]
    removed_courses = [it for code, it in items_a.items() if code not in items_b]

    moved_courses = []
    for code, it_b in items_b.items():
        if code in items_a:
            it_a = items_a[code]
            if (
                it_a["term_index"] != it_b["term_index"]
                or it_a["term_code"] != it_b["term_code"]
            ):
                moved_courses.append(
                    {
                        "course_code": code,
                        "from_term_code": it_a["term_code"],
                        "from_term_index": it_a["term_index"],
                        "to_term_code": it_b["term_code"],
                        "to_term_index": it_b["term_index"],
                    }
                )

    sim_a = version_a.snapshot_data.get("simulation", {})
    sim_b = version_b.snapshot_data.get("simulation", {})

    return {
        "version_a_number": version_a.version_number,
        "version_b_number": version_b.version_number,
        "added_courses": added_courses,
        "removed_courses": removed_courses,
        "moved_courses": moved_courses,
        "version_a_grad_term": sim_a.get("projected_graduation_term"),
        "version_b_grad_term": sim_b.get("projected_graduation_term"),
        "version_a_planned_credits": sim_a.get("total_planned_credits"),
        "version_b_planned_credits": sim_b.get("total_planned_credits"),
    }
