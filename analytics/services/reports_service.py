import datetime
from decimal import Decimal
from typing import Any, Optional

from django.db import models
from django.db.models import (
    Avg,
    Case,
    Count,
    F,
    Max,
    Min,
    Sum,
    When,
)

from academic_records.models import (
    StudentRecord,
    StudentRecordStatus,
    TranscriptEntry,
)
from accounts.models import AdvisorAssignment, InstitutionMembership, Role
from advising.models import OverallRiskLevel, StudentRiskProfile
from curriculum.models import CourseOffering
from institutions.models import Institution
from planning.models import (
    Plan,
    PlanItem,
    PlanReviewDecision,
    PlanStatus,
    ReviewAction,
)


def get_programme_progress_report(
    institution: Institution,
    programme_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Computes degree progress distribution for students enrolled across programmes.
    Categorizes student progress into brackets (0-25%, 26-50%, 51-75%, 76-100%, Near Completion)
    using pure database aggregations.
    """
    qs = StudentRecord.objects.filter(
        institution=institution,
        status=StudentRecordStatus.ACTIVE,
    )
    if programme_id:
        qs = qs.filter(programme_id=programme_id)

    # Aggregate by programme and curriculum
    programmes_data = (
        qs.values(
            "programme__id",
            "programme__code",
            "programme__name",
            "pinned_curriculum__total_credits_required",
        )
        .annotate(
            total_students=Count("id"),
            avg_cgpa=Avg("cached_cgpa"),
            avg_earned_credits=Avg("cached_total_credits"),
            # Brackets based on curriculum total credits:
            # 0 - 25% (credits < 0.25 * total_credits_required)
            bracket_0_25=Count(
                Case(
                    When(
                        cached_total_credits__lt=F("pinned_curriculum__total_credits_required") * Decimal("0.25"),
                        then=1,
                    ),
                    output_field=models.IntegerField(),
                )
            ),
            # 26 - 50%
            bracket_26_50=Count(
                Case(
                    When(
                        cached_total_credits__gte=F("pinned_curriculum__total_credits_required") * Decimal("0.25"),
                        cached_total_credits__lt=F("pinned_curriculum__total_credits_required") * Decimal("0.50"),
                        then=1,
                    ),
                    output_field=models.IntegerField(),
                )
            ),
            # 51 - 75%
            bracket_51_75=Count(
                Case(
                    When(
                        cached_total_credits__gte=F("pinned_curriculum__total_credits_required") * Decimal("0.50"),
                        cached_total_credits__lt=F("pinned_curriculum__total_credits_required") * Decimal("0.75"),
                        then=1,
                    ),
                    output_field=models.IntegerField(),
                )
            ),
            # 76 - 100%
            bracket_76_100=Count(
                Case(
                    When(
                        cached_total_credits__gte=F("pinned_curriculum__total_credits_required") * Decimal("0.75"),
                        then=1,
                    ),
                    output_field=models.IntegerField(),
                )
            ),
            # Near completion (>= 90% credits)
            near_completion=Count(
                Case(
                    When(
                        cached_total_credits__gte=F("pinned_curriculum__total_credits_required") * Decimal("0.90"),
                        then=1,
                    ),
                    output_field=models.IntegerField(),
                )
            ),
        )
        .order_by("programme__code")
    )

    items = []
    total_enrolled = 0
    for p in programmes_data:
        total_enrolled += p["total_students"]
        avg_cgpa_val = float(p["avg_cgpa"]) if p["avg_cgpa"] is not None else 0.0
        avg_credits_val = float(p["avg_earned_credits"]) if p["avg_earned_credits"] is not None else 0.0
        min_credits = (
            float(p["pinned_curriculum__total_credits_required"])
            if p["pinned_curriculum__total_credits_required"] is not None
            else 120.0
        )
        items.append({
            "programme_id": str(p["programme__id"]),
            "programme_code": p["programme__code"],
            "programme_name": p["programme__name"],
            "min_credits_required": min_credits,
            "total_students": p["total_students"],
            "avg_cgpa": round(avg_cgpa_val, 2),
            "avg_earned_credits": round(avg_credits_val, 1),
            "bracket_0_25": p["bracket_0_25"],
            "bracket_26_50": p["bracket_26_50"],
            "bracket_51_75": p["bracket_51_75"],
            "bracket_76_100": p["bracket_76_100"],
            "near_completion": p["near_completion"],
        })


    return {
        "report": "programme_progress",
        "total_programmes": len(items),
        "total_students_enrolled": total_enrolled,
        "items": items,
    }


def get_prerequisite_blockers_report(
    institution: Institution,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Identifies the most common course prerequisite bottlenecks across the institution.
    Aggregates courses with unpassed transcript attempts (FAILED / WITHDRAWN) and counts
    how many distinct active students are impacted.
    """
    failed_attempts = (
        TranscriptEntry.objects.filter(
            institution=institution,
            status__in=["FAILED", "WITHDRAWN"],
            student_record__status=StudentRecordStatus.ACTIVE,
        )
        .values("course__id", "course__code", "course__title", "course__credits")
        .annotate(
            impacted_students_count=Count("student_record", distinct=True),
            total_unpassed_attempts=Count("id"),
        )
        .order_by("-impacted_students_count", "-total_unpassed_attempts")[:limit]
    )

    items = []
    for f in failed_attempts:
        items.append({
            "course_id": str(f["course__id"]),
            "course_code": f["course__code"],
            "course_name": f["course__title"],
            "credits": float(f["course__credits"]) if f["course__credits"] is not None else 0.0,
            "impacted_students_count": f["impacted_students_count"],
            "total_unpassed_attempts": f["total_unpassed_attempts"],
        })

    return {
        "report": "prerequisite_blockers",
        "total_blockers_identified": len(items),
        "items": items,
    }


def get_advisor_workload_report(
    institution: Institution,
    advisor_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Computes advisor advising workloads, pending reviews, and advisee risk level distribution.
    """
    memberships_qs = InstitutionMembership.objects.filter(
        institution=institution,
        role=Role.ADVISOR,
        is_active=True,
    ).select_related("user")

    if advisor_id:
        memberships_qs = memberships_qs.filter(user_id=advisor_id)

    items = []
    total_assigned = 0
    total_pending_plans = 0

    for mem in memberships_qs:
        # Active assignments for this advisor
        advisees_assignments = AdvisorAssignment.objects.filter(
            institution=institution,
            advisor=mem,
            is_active=True,
        )
        advisee_student_ids = advisees_assignments.values_list("student__user_id", flat=True)
        advisee_count = advisees_assignments.count()
        total_assigned += advisee_count

        # Pending plans for advisees
        pending_plans_count = Plan.objects.filter(
            institution=institution,
            student_record__student_id__in=advisee_student_ids,
            status__in=[PlanStatus.SUBMITTED, PlanStatus.RESUBMITTED, PlanStatus.UNDER_REVIEW],
        ).count()
        total_pending_plans += pending_plans_count

        # Completed reviews by this advisor
        completed_reviews_count = PlanReviewDecision.objects.filter(
            institution=institution,
            reviewer=mem.user,
            action__in=[ReviewAction.APPROVE, ReviewAction.RETURN, ReviewAction.REJECT],
        ).count()

        # Risk distribution among advisees
        risk_summary = (
            StudentRiskProfile.objects.filter(
                institution=institution,
                student_record__student_id__in=advisee_student_ids,
            )
            .values("overall_risk_level")
            .annotate(count=Count("id"))
        )
        risk_dict = {r["overall_risk_level"]: r["count"] for r in risk_summary}

        advisor_name = (
            f"{mem.user.first_name} {mem.user.last_name}".strip() or mem.user.username
        )

        items.append({
            "advisor_id": str(mem.user.id),
            "advisor_username": mem.user.username,
            "advisor_name": advisor_name,
            "assigned_advisees_count": advisee_count,
            "pending_plans_count": pending_plans_count,
            "completed_reviews_count": completed_reviews_count,
            "critical_risk_advisees": risk_dict.get(OverallRiskLevel.CRITICAL, 0),
            "high_risk_advisees": risk_dict.get(OverallRiskLevel.HIGH, 0),
            "medium_risk_advisees": risk_dict.get(OverallRiskLevel.MEDIUM, 0),
            "low_risk_advisees": risk_dict.get(OverallRiskLevel.LOW, 0),
        })

    items.sort(key=lambda x: -x["assigned_advisees_count"])

    return {
        "report": "advisor_workload",
        "total_advisors": len(items),
        "total_active_advisee_assignments": total_assigned,
        "total_pending_reviews": total_pending_plans,
        "items": items,
    }


def get_approval_turnaround_report(
    institution: Institution,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
) -> dict[str, Any]:
    """
    Computes time-to-decision turnaround metrics for submitted graduation plans.
    Calculates elapsed time between plan version submission and advisor review decision.
    """
    decisions_qs = PlanReviewDecision.objects.filter(
        institution=institution,
        action__in=[ReviewAction.APPROVE, ReviewAction.RETURN, ReviewAction.REJECT],
        plan_version__submitted_at__isnull=False,
    ).select_related("reviewer", "plan_version")

    if start_date:
        decisions_qs = decisions_qs.filter(created_at__date__gte=start_date)
    if end_date:
        decisions_qs = decisions_qs.filter(created_at__date__lte=end_date)

    turnaround_expr = ExpressionWrapper(
        F("created_at") - F("plan_version__submitted_at"),
        output_field=models.DurationField(),
    )

    annotated_qs = decisions_qs.annotate(turnaround=turnaround_expr)
    total_decisions = annotated_qs.count()

    overall_metrics = annotated_qs.aggregate(
        avg_turnaround=Avg("turnaround"),
        min_turnaround=Min("turnaround"),
        max_turnaround=Max("turnaround"),
    )

    def td_to_hours(td: Optional[datetime.timedelta]) -> float:
        if td is None:
            return 0.0
        return round(td.total_seconds() / 3600.0, 2)

    # Per-reviewer breakdown
    reviewer_stats = (
        annotated_qs.values("reviewer__id", "reviewer__username", "reviewer__first_name", "reviewer__last_name")
        .annotate(
            decisions_count=Count("id"),
            avg_turnaround=Avg("turnaround"),
        )
        .order_by("-decisions_count")
    )

    reviewer_items = []
    for r in reviewer_stats:
        rev_name = f"{r['reviewer__first_name']} {r['reviewer__last_name']}".strip() or r["reviewer__username"]
        reviewer_items.append({
            "reviewer_id": str(r["reviewer__id"]),
            "reviewer_name": rev_name,
            "decisions_count": r["decisions_count"],
            "avg_turnaround_hours": td_to_hours(r["avg_turnaround"]),
        })

    # Action breakdown
    action_stats = (
        annotated_qs.values("action")
        .annotate(
            count=Count("id"),
            avg_turnaround=Avg("turnaround"),
        )
    )
    action_items = [
        {
            "action": a["action"],
            "count": a["count"],
            "avg_turnaround_hours": td_to_hours(a["avg_turnaround"]),
        }
        for a in action_stats
    ]

    return {
        "report": "approval_turnaround",
        "total_decisions": total_decisions,
        "avg_turnaround_hours": td_to_hours(overall_metrics["avg_turnaround"]),
        "min_turnaround_hours": td_to_hours(overall_metrics["min_turnaround"]),
        "max_turnaround_hours": td_to_hours(overall_metrics["max_turnaround"]),
        "reviewer_breakdown": reviewer_items,
        "action_breakdown": action_items,
    }


# ExpressionWrapper import
from django.db.models import ExpressionWrapper  # noqa: E402


def get_plan_approval_funnel_report(
    institution: Institution,
    programme_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Computes plan lifecycle status distribution and stage conversion percentages across
    Draft -> Submitted -> Under Review -> Approved / Returned / Rejected.
    """
    plans_qs = Plan.objects.filter(institution=institution)
    if programme_id:
        plans_qs = plans_qs.filter(student_record__programme_id=programme_id)

    status_counts = plans_qs.values("status").annotate(count=Count("id"))
    status_map = {s["status"]: s["count"] for s in status_counts}

    total_plans = plans_qs.count()
    draft_count = status_map.get(PlanStatus.DRAFT, 0)
    submitted_count = status_map.get(PlanStatus.SUBMITTED, 0)
    under_review_count = status_map.get(PlanStatus.UNDER_REVIEW, 0)
    resubmitted_count = status_map.get(PlanStatus.RESUBMITTED, 0)
    approved_count = status_map.get(PlanStatus.APPROVED, 0)
    returned_count = status_map.get(PlanStatus.RETURNED, 0)
    rejected_count = status_map.get(PlanStatus.REJECTED, 0)
    superseded_count = status_map.get(PlanStatus.SUPERSEDED, 0)
    archived_count = status_map.get(PlanStatus.ARCHIVED, 0)

    # Conversion calculations
    ever_submitted = total_plans - draft_count
    submission_rate = round((ever_submitted / total_plans * 100), 1) if total_plans > 0 else 0.0

    reviewed_or_underway = under_review_count + approved_count + returned_count + rejected_count
    review_initiation_rate = (
        round((reviewed_or_underway / ever_submitted * 100), 1) if ever_submitted > 0 else 0.0
    )

    total_decided = approved_count + returned_count + rejected_count
    approval_rate = round((approved_count / total_decided * 100), 1) if total_decided > 0 else 0.0
    revision_rate = round((returned_count / total_decided * 100), 1) if total_decided > 0 else 0.0

    return {
        "report": "plan_funnel",
        "total_plans": total_plans,
        "stages": {
            "draft": draft_count,
            "submitted": submitted_count + resubmitted_count,
            "under_review": under_review_count,
            "approved": approved_count,
            "returned_for_revision": returned_count,
            "rejected": rejected_count,
            "superseded": superseded_count,
            "archived": archived_count,
        },
        "conversion_rates": {
            "submission_rate_pct": submission_rate,
            "review_initiation_rate_pct": review_initiation_rate,
            "approval_rate_pct": approval_rate,
            "revision_requested_rate_pct": revision_rate,
        },
    }


def get_risk_distribution_report(
    institution: Institution,
    programme_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Aggregates academic risk levels and indicator distributions across assessed students,
    consuming StudentRiskProfile from Phase 08E.
    """
    profiles_qs = StudentRiskProfile.objects.filter(institution=institution)
    if programme_id:
        profiles_qs = profiles_qs.filter(student_record__programme_id=programme_id)

    total_assessed = profiles_qs.count()

    risk_counts = profiles_qs.values("overall_risk_level").annotate(count=Count("id"))
    risk_map = {r["overall_risk_level"]: r["count"] for r in risk_counts}

    aggregates = profiles_qs.aggregate(
        total_critical_risks=Sum("critical_risk_count"),
        total_warning_risks=Sum("warning_risk_count"),
        total_active_risks=Sum("active_risk_count"),
        avg_active_risks=Avg("active_risk_count"),
    )

    # Programme-level risk breakdown
    programme_breakdown = (
        profiles_qs.values(
            "student_record__programme__id",
            "student_record__programme__code",
            "student_record__programme__name",
        )
        .annotate(
            total_students=Count("id"),
            critical_count=Count(
                Case(When(overall_risk_level=OverallRiskLevel.CRITICAL, then=1), output_field=models.IntegerField())
            ),
            high_count=Count(
                Case(When(overall_risk_level=OverallRiskLevel.HIGH, then=1), output_field=models.IntegerField())
            ),
            medium_count=Count(
                Case(When(overall_risk_level=OverallRiskLevel.MEDIUM, then=1), output_field=models.IntegerField())
            ),
            low_count=Count(
                Case(When(overall_risk_level=OverallRiskLevel.LOW, then=1), output_field=models.IntegerField())
            ),
        )
        .order_by("student_record__programme__code")
    )

    programme_items = [
        {
            "programme_id": str(p["student_record__programme__id"]),
            "programme_code": p["student_record__programme__code"],
            "programme_name": p["student_record__programme__name"],
            "total_students": p["total_students"],
            "critical_risk_count": p["critical_count"],
            "high_risk_count": p["high_count"],
            "medium_risk_count": p["medium_count"],
            "low_risk_count": p["low_count"],
        }
        for p in programme_breakdown
    ]

    return {
        "report": "risk_distribution",
        "total_students_assessed": total_assessed,
        "risk_levels": {
            "critical": risk_map.get(OverallRiskLevel.CRITICAL, 0),
            "high": risk_map.get(OverallRiskLevel.HIGH, 0),
            "medium": risk_map.get(OverallRiskLevel.MEDIUM, 0),
            "low": risk_map.get(OverallRiskLevel.LOW, 0),
        },
        "aggregate_indicators": {
            "total_critical_indicators": aggregates["total_critical_risks"] or 0,
            "total_warning_indicators": aggregates["total_warning_risks"] or 0,
            "total_active_indicators": aggregates["total_active_risks"] or 0,
            "avg_active_indicators_per_student": round(float(aggregates["avg_active_risks"] or 0.0), 2),
        },
        "programme_breakdown": programme_items,
    }


def get_elective_demand_report(
    institution: Institution,
    term_id: Optional[str] = None,
    limit: int = 25,
) -> dict[str, Any]:
    """
    Projects student elective course demand in upcoming terms by aggregating planned
    electives from student graduation plans against course offering capacities.
    """
    items_qs = PlanItem.objects.filter(
        plan__institution=institution,
        plan__status__in=[
            PlanStatus.APPROVED,
            PlanStatus.SUBMITTED,
            PlanStatus.UNDER_REVIEW,
            PlanStatus.DRAFT,
        ],
    ).select_related("course", "planned_term")

    if term_id:
        if isinstance(term_id, int) or (isinstance(term_id, str) and term_id.isdigit()):
            items_qs = items_qs.filter(planned_term_id=int(term_id))
        else:
            items_qs = items_qs.filter(planned_term__code=str(term_id))

    demand_query = (
        items_qs.values(
            "course__id",
            "course__code",
            "course__title",
            "planned_term__id",
            "planned_term__code",
            "planned_term__name",
            "planned_term__season",
            "planned_term__year",
        )
        .annotate(demand_count=Count("id"))
        .order_by("-demand_count")[:limit]
    )

    items = []
    for d in demand_query:
        course_id = d["course__id"]
        planned_term_id = d["planned_term__id"]

        # Check total capacity scheduled in course offerings
        offering_stats = CourseOffering.objects.filter(
            institution=institution,
            course_id=course_id,
            academic_term=d["planned_term__season"],
            academic_year=str(d["planned_term__year"]),
            is_offered=True,
        ).aggregate(
            total_capacity=Sum("capacity"),
        )

        capacity = offering_stats["total_capacity"] or 0
        enrolled = TranscriptEntry.objects.filter(
            institution=institution,
            course_id=course_id,
            term_id=planned_term_id,
            status__in=["ENROLLED", "IN_PROGRESS"],
        ).count()
        projected_deficit = max(0, d["demand_count"] - capacity) if capacity > 0 else 0

        items.append({
            "course_id": str(course_id),
            "course_code": d["course__code"],
            "course_name": d["course__title"],
            "term_code": d["planned_term__code"],
            "term_name": d["planned_term__name"],
            "student_demand_count": d["demand_count"],
            "scheduled_capacity": capacity,
            "currently_enrolled": enrolled,
            "projected_capacity_deficit": projected_deficit,
        })

    return {
        "report": "elective_demand",
        "total_items_projected": len(items),
        "items": items,
    }


def get_analytics_overview_summary(institution: Institution) -> dict[str, Any]:
    """
    Executive dashboard metrics combining high-level counts, turnaround time,
    and institutional risk indicators.
    """
    active_students = StudentRecord.objects.filter(
        institution=institution,
        status=StudentRecordStatus.ACTIVE,
    ).count()

    active_plans = Plan.objects.filter(institution=institution).count()
    plans_under_review = Plan.objects.filter(
        institution=institution,
        status__in=[PlanStatus.SUBMITTED, PlanStatus.RESUBMITTED, PlanStatus.UNDER_REVIEW],
    ).count()

    critical_high_risks = StudentRiskProfile.objects.filter(
        institution=institution,
        overall_risk_level__in=[OverallRiskLevel.CRITICAL, OverallRiskLevel.HIGH],
    ).count()

    turnaround_data = get_approval_turnaround_report(institution)
    top_blockers = get_prerequisite_blockers_report(institution, limit=3)

    return {
        "total_active_students": active_students,
        "total_plans": active_plans,
        "plans_pending_review": plans_under_review,
        "critical_or_high_risk_students": critical_high_risks,
        "avg_approval_turnaround_hours": turnaround_data["avg_turnaround_hours"],
        "top_bottlenecks": top_blockers["items"],
    }
