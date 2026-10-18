from typing import Any

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone

from academic_records.models import StudentRecord
from advising.models import OverallRiskLevel, RiskCategory, RiskSeverity, StudentRiskProfile
from advising.services.risk_evaluators import (
    evaluate_credit_shortfall,
    evaluate_missing_critical_prerequisites,
    evaluate_prerequisite_bottlenecks,
    evaluate_registration_deadlines,
    evaluate_repeated_course_failures,
    evaluate_required_courses_unoffered,
)
from advising.services.risk_models import RiskEvaluationResult, RiskIndicator
from institutions.models import Institution
from planning.models import Plan


def evaluate_student_risks(
    student_record: StudentRecord,
    plan: Plan | None = None,
    save: bool = True,
    assessed_by: User | None = None,
) -> RiskEvaluationResult:
    """
    Evaluates transparent, rule-based academic risk indicators for a student.
    Contains zero machine learning or black-box heuristics.
    """
    all_indicators: list[RiskIndicator] = []

    # 1. Missing Critical Prerequisites
    all_indicators.extend(evaluate_missing_critical_prerequisites(student_record, plan))

    # 2. Required Courses Unoffered in Remaining Terms
    all_indicators.extend(evaluate_required_courses_unoffered(student_record, plan))

    # 3. Registration Deadline Approaching with 0 Courses
    all_indicators.extend(evaluate_registration_deadlines(student_record, plan))

    # 4. Credit Shortfall vs Remaining Terms
    all_indicators.extend(evaluate_credit_shortfall(student_record, plan))

    # 5. Repeated Course Failures
    all_indicators.extend(evaluate_repeated_course_failures(student_record))

    # 6. Prerequisite Bottlenecks
    all_indicators.extend(evaluate_prerequisite_bottlenecks(student_record))

    # Deterministic sorting: CRITICAL first, then WARNING, then INFO, tie-broken by code
    severity_order: dict[str, int] = {str(RiskSeverity.CRITICAL): 0, str(RiskSeverity.WARNING): 1, str(RiskSeverity.INFO): 2}
    all_indicators.sort(key=lambda x: (severity_order.get(x.severity, 99), x.code, x.name))

    critical_count = sum(1 for i in all_indicators if i.severity == RiskSeverity.CRITICAL)
    warning_count = sum(1 for i in all_indicators if i.severity == RiskSeverity.WARNING)
    info_count = sum(1 for i in all_indicators if i.severity == RiskSeverity.INFO)
    active_count = len(all_indicators)

    # Compute overall risk level deterministically
    if critical_count >= 1:
        overall_level = OverallRiskLevel.CRITICAL
    elif warning_count >= 2:
        overall_level = OverallRiskLevel.HIGH
    elif warning_count == 1:
        overall_level = OverallRiskLevel.MEDIUM
    else:
        overall_level = OverallRiskLevel.LOW

    # Generate transparent summary string
    if critical_count > 0:
        summary = (
            f"Critical academic attention required: {critical_count} critical and {warning_count} warning indicator(s) identified."
        )
    elif warning_count > 0:
        summary = (
            f"Moderate academic risk: {warning_count} warning indicator(s) identified. Advising intervention recommended."
        )
    else:
        summary = "No immediate academic risks identified. Student is progressing on track."

    result = RiskEvaluationResult(
        student_id=str(student_record.id),
        student_username=student_record.student.username,
        institution_id=str(student_record.institution_id),
        overall_risk_level=overall_level,
        active_risk_count=active_count,
        critical_risk_count=critical_count,
        warning_risk_count=warning_count,
        info_risk_count=info_count,
        indicators=all_indicators,
        assessed_at=timezone.now().isoformat(),
        summary=summary,
    )

    if save:
        indicators_json = [ind.to_dict() for ind in all_indicators]
        StudentRiskProfile.objects.update_or_create(
            institution=student_record.institution,
            student_record=student_record,
            defaults={
                "overall_risk_level": overall_level,
                "active_risk_count": active_count,
                "critical_risk_count": critical_count,
                "warning_risk_count": warning_count,
                "info_risk_count": info_count,
                "indicators": indicators_json,
                "summary": summary,
                "last_assessed_by": assessed_by,
            },
        )

    return result


def get_student_risk_profile(
    student_record: StudentRecord,
    refresh: bool = False,
    user: User | None = None,
) -> RiskEvaluationResult:
    """
    Fetches the existing cached risk profile or evaluates a fresh one.
    """
    if not refresh:
        profile = StudentRiskProfile.objects.filter(
            institution=student_record.institution,
            student_record=student_record,
        ).first()

        if profile:
            indicators: list[RiskIndicator] = []
            for item in profile.indicators:
                indicators.append(
                    RiskIndicator(
                        code=item.get("code", ""),
                        name=item.get("name", ""),
                        severity=item.get("severity", RiskSeverity.INFO),
                        category=item.get("category", RiskCategory.ACADEMIC_STANDING),
                        message=item.get("message", ""),
                        contributing_factors=item.get("contributing_factors", {}),
                        source_records=item.get("source_records", []),
                        actionable_recommendation=item.get("actionable_recommendation", ""),
                    )
                )

            return RiskEvaluationResult(
                student_id=str(student_record.id),
                student_username=student_record.student.username,
                institution_id=str(student_record.institution_id),
                overall_risk_level=profile.overall_risk_level,
                active_risk_count=profile.active_risk_count,
                critical_risk_count=profile.critical_risk_count,
                warning_risk_count=profile.warning_risk_count,
                info_risk_count=profile.info_risk_count,
                indicators=indicators,
                assessed_at=profile.assessed_at.isoformat(),
                summary=profile.summary,
            )

    return evaluate_student_risks(student_record, save=True, assessed_by=user)


def get_institution_risk_summary(
    institution: Institution,
    programme_code: str | None = None,
) -> dict[str, Any]:
    """
    Aggregates institution-wide risk metrics via SQL database aggregation.
    Does not load student records into Python.
    """
    qs = StudentRiskProfile.objects.filter(institution=institution)
    if programme_code:
        qs = qs.filter(student_record__programme__code=programme_code)

    total_profiles = qs.count()

    counts = qs.aggregate(
        critical=Count("id", filter=Q(overall_risk_level=OverallRiskLevel.CRITICAL)),
        high=Count("id", filter=Q(overall_risk_level=OverallRiskLevel.HIGH)),
        medium=Count("id", filter=Q(overall_risk_level=OverallRiskLevel.MEDIUM)),
        low=Count("id", filter=Q(overall_risk_level=OverallRiskLevel.LOW)),
    )

    return {
        "institution_id": str(institution.id),
        "institution_name": institution.name,
        "programme_code": programme_code,
        "total_assessed_students": total_profiles,
        "risk_level_counts": {
            "CRITICAL": counts.get("critical", 0),
            "HIGH": counts.get("high", 0),
            "MEDIUM": counts.get("medium", 0),
            "LOW": counts.get("low", 0),
        },
        "critical_percentage": round(
            (counts.get("critical", 0) / total_profiles * 100.0) if total_profiles > 0 else 0.0,
            1,
        ),
        "action_required_count": counts.get("critical", 0) + counts.get("high", 0),
    }
