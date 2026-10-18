from typing import Any

from django.utils import timezone

from academic_records.models import AcademicTerm, StudentRecord, TranscriptEntry
from advising.models import RiskCategory, RiskSeverity
from advising.services.risk_models import RiskIndicator, SourceRecordReference
from curriculum.models import Course, CourseOffering, PrerequisiteRule
from degree_audit.services.audit_service import run_degree_audit
from eligibility.services.eligibility_service import check_course_eligibility
from planning.models import Plan, PlanItem


def get_passed_course_ids(student_record: StudentRecord) -> set[str]:
    """Returns set of course UUID strings passed by student."""
    passing_grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "P", "S", "CR"}
    return {
        str(cid)
        for cid in TranscriptEntry.objects.filter(
            student_record=student_record,
            grade__in=passing_grades,
        ).values_list("course_id", flat=True)
    }


def evaluate_missing_critical_prerequisites(
    student_record: StudentRecord,
    plan: Plan | None = None,
) -> list[RiskIndicator]:
    """
    Flags mandatory degree requirements or planned upcoming courses whose prerequisites are not met.
    Zero machine learning; uses pure-Python prerequisite engine.
    """
    indicators: list[RiskIndicator] = []
    passed_ids = get_passed_course_ids(student_record)
    pinned_cv = student_record.pinned_curriculum
    if not pinned_cv:
        return indicators

    # 1. Identify uncompleted mandatory courses from pinned curriculum
    mandatory_courses: list[Course] = list(
        Course.objects.filter(
            group_memberships__requirement_group__curriculum_version=pinned_cv,
            group_memberships__is_mandatory=True,
        ).distinct()
    )

    # 2. Plus courses planned in the given plan
    planned_courses: list[Course] = []
    if plan:
        planned_courses = list(
            Course.objects.filter(
                plan_items__plan=plan
            ).distinct()
        )

    candidate_courses_dict: dict[str, Course] = {}
    for c in mandatory_courses:
        if str(c.id) not in passed_ids:
            candidate_courses_dict[str(c.id)] = c
    for c in planned_courses:
        if str(c.id) not in passed_ids:
            candidate_courses_dict[str(c.id)] = c

    for c_id, course in candidate_courses_dict.items():
        prereq_rule = PrerequisiteRule.objects.filter(
            curriculum_version=pinned_cv,
            course=course,
        ).first()

        if not prereq_rule or not prereq_rule.rule_json:
            continue

        eligibility_res = check_course_eligibility(student_record, course)
        if not eligibility_res.eligible:
            blockers = eligibility_res.blocking_reasons
            blockers_str = "; ".join(blockers) if blockers else "Prerequisite conditions not met"
            is_mandatory = any(c.id == course.id for c in mandatory_courses)

            source_records = [
                SourceRecordReference(
                    entity_type="Course",
                    record_id=str(course.id),
                    display_name=f"{course.code} - {course.title}",
                ).to_dict(),
                SourceRecordReference(
                    entity_type="StudentRecord",
                    record_id=str(student_record.id),
                    display_name=student_record.student.username,
                ).to_dict(),
                SourceRecordReference(
                    entity_type="PrerequisiteRule",
                    record_id=str(prereq_rule.id),
                    display_name=f"{course.code} Prerequisite Rule",
                ).to_dict(),
            ]

            indicators.append(
                RiskIndicator(
                    code="MISSING_CRITICAL_PREREQUISITE",
                    name="Missing Critical Prerequisite",
                    severity=RiskSeverity.CRITICAL if is_mandatory else RiskSeverity.WARNING,
                    category=RiskCategory.PREREQUISITE,
                    message=(
                        f"Prerequisite requirements for {'mandatory ' if is_mandatory else ''}course "
                        f"'{course.code} - {course.title}' are not satisfied: {blockers_str}."
                    ),
                    contributing_factors={
                        "course_code": course.code,
                        "course_title": course.title,
                        "is_mandatory": is_mandatory,
                        "rule_type": prereq_rule.rule_json.get("type") or prereq_rule.rule_json.get("rule_type", "PREREQUISITE"),
                        "blocking_reasons": blockers,
                        "status": eligibility_res.status,
                    },
                    source_records=source_records,
                    actionable_recommendation=(
                        f"Complete required prerequisite courses before attempting to register for {course.code}."
                    ),
                )
            )

    return indicators


def evaluate_required_courses_unoffered(
    student_record: StudentRecord,
    plan: Plan | None = None,
) -> list[RiskIndicator]:
    """
    Identifies mandatory degree requirements that have no scheduled offerings across remaining terms.
    """
    indicators: list[RiskIndicator] = []
    passed_ids = get_passed_course_ids(student_record)
    pinned_cv = student_record.pinned_curriculum
    if not pinned_cv:
        return indicators

    # Uncompleted mandatory courses
    unearned_mandatory = list(
        Course.objects.filter(
            group_memberships__requirement_group__curriculum_version=pinned_cv,
            group_memberships__is_mandatory=True,
        ).exclude(id__in=passed_ids).distinct()
    )

    if not unearned_mandatory:
        return indicators

    today = timezone.now().date()
    # Upcoming active academic terms
    upcoming_terms = list(
        AcademicTerm.objects.filter(
            institution=student_record.institution,
            is_active=True,
            start_date__gte=today,
        ).order_by("start_date")[:8]
    )

    if not upcoming_terms:
        return indicators

    upcoming_seasons = {t.season.upper() for t in upcoming_terms}
    upcoming_term_codes = [t.code for t in upcoming_terms]

    for course in unearned_mandatory:
        # Check active course offerings for this course in upcoming seasons or years
        offerings = CourseOffering.objects.filter(
            institution=student_record.institution,
            course=course,
            is_offered=True,
        )

        has_upcoming_offering = False
        for off in offerings:
            term_str = str(off.academic_term).upper()
            if any(season in term_str for season in upcoming_seasons) or off.academic_term in upcoming_term_codes:
                has_upcoming_offering = True
                break

        if not has_upcoming_offering:
            source_records = [
                SourceRecordReference(
                    entity_type="Course",
                    record_id=str(course.id),
                    display_name=f"{course.code} - {course.title}",
                ).to_dict(),
                SourceRecordReference(
                    entity_type="StudentRecord",
                    record_id=str(student_record.id),
                    display_name=student_record.student.username,
                ).to_dict(),
            ]

            indicators.append(
                RiskIndicator(
                    code="REQUIRED_COURSE_UNOFFERED",
                    name="Required Course Not Offered in Remaining Terms",
                    severity=RiskSeverity.CRITICAL,
                    category=RiskCategory.COURSE_OFFERING,
                    message=(
                        f"Mandatory degree requirement '{course.code} - {course.title}' has no scheduled "
                        f"course offerings across the {len(upcoming_terms)} upcoming academic terms."
                    ),
                    contributing_factors={
                        "course_code": course.code,
                        "course_title": course.title,
                        "upcoming_terms_checked": upcoming_term_codes,
                        "upcoming_terms_count": len(upcoming_terms),
                        "offerings_found": 0,
                        "is_mandatory": True,
                    },
                    source_records=source_records,
                    actionable_recommendation=(
                        f"Contact Academic Coordinator to request a course offering or an approved course substitution for {course.code}."
                    ),
                )
            )

    return indicators


def evaluate_registration_deadlines(
    student_record: StudentRecord,
    plan: Plan | None = None,
    threshold_days: int = 14,
) -> list[RiskIndicator]:
    """
    Flags when an academic term is starting within N days and the student has no courses registered or planned.
    """
    indicators: list[RiskIndicator] = []
    today = timezone.now().date()

    # Find the imminent upcoming term
    imminent_term = (
        AcademicTerm.objects.filter(
            institution=student_record.institution,
            is_active=True,
            start_date__gte=today,
        )
        .order_by("start_date")
        .first()
    )

    if not imminent_term:
        return indicators

    days_until_start = (imminent_term.start_date - today).days
    if days_until_start > threshold_days:
        return indicators

    # Check if student is enrolled or registered in any course for this imminent term
    enrolled_count = TranscriptEntry.objects.filter(
        student_record=student_record,
        term=imminent_term,
    ).count()

    planned_count = 0
    if plan:
        planned_count = PlanItem.objects.filter(
            plan=plan,
            planned_term=imminent_term,
        ).count()

    total_courses_for_term = enrolled_count + planned_count
    if total_courses_for_term == 0:
        severity = RiskSeverity.CRITICAL if days_until_start <= 3 else RiskSeverity.WARNING
        source_records = [
            SourceRecordReference(
                entity_type="AcademicTerm",
                record_id=str(imminent_term.id),
                display_name=f"{imminent_term.code} - {imminent_term.name}",
            ).to_dict(),
            SourceRecordReference(
                entity_type="StudentRecord",
                record_id=str(student_record.id),
                display_name=student_record.student.username,
            ).to_dict(),
        ]

        indicators.append(
            RiskIndicator(
                code="REGISTRATION_DEADLINE_APPROACHING",
                name="Registration Deadline Approaching",
                severity=severity,
                category=RiskCategory.REGISTRATION,
                message=(
                    f"Upcoming term '{imminent_term.name}' starts in {days_until_start} days, "
                    f"but no courses are currently planned or enrolled."
                ),
                contributing_factors={
                    "term_code": imminent_term.code,
                    "term_name": imminent_term.name,
                    "term_start_date": imminent_term.start_date.isoformat(),
                    "days_until_start": days_until_start,
                    "threshold_days": threshold_days,
                    "enrolled_course_count": enrolled_count,
                    "planned_course_count": planned_count,
                },
                source_records=source_records,
                actionable_recommendation=(
                    f"Select and register for courses for {imminent_term.name} immediately to ensure timely matriculation."
                ),
            )
        )

    return indicators


def evaluate_credit_shortfall(
    student_record: StudentRecord,
    plan: Plan | None = None,
    max_standard_credits: float = 18.0,
) -> list[RiskIndicator]:
    """
    Evaluates whether remaining required credits can be completed within remaining terms at standard load.
    """
    indicators: list[RiskIndicator] = []
    audit_report = run_degree_audit(student_record)
    remaining_credits = float(audit_report.remaining_credits_required)

    if remaining_credits <= 0:
        return indicators

    # Determine remaining terms count
    remaining_terms = 0
    if plan:
        remaining_terms = (
            PlanItem.objects.filter(plan=plan)
            .values("planned_term")
            .distinct()
            .count()
        )

    if remaining_terms <= 0:
        # Default estimation: standard 4-year degree (8 terms) minus terms attempted, min 1
        terms_attempted = (
            TranscriptEntry.objects.filter(student_record=student_record)
            .values("term")
            .distinct()
            .count()
        )
        remaining_terms = max(1, 8 - terms_attempted)

    required_velocity = remaining_credits / float(remaining_terms)
    max_capacity = float(remaining_terms) * max_standard_credits

    if required_velocity > max_standard_credits or remaining_credits > max_capacity:
        credit_deficit = round(remaining_credits - max_capacity, 2)
        source_records = [
            SourceRecordReference(
                entity_type="StudentRecord",
                record_id=str(student_record.id),
                display_name=student_record.student.username,
            ).to_dict(),
            SourceRecordReference(
                entity_type="Programme",
                record_id=str(student_record.programme.id),
                display_name=student_record.programme.name,
            ).to_dict(),
        ]

        indicators.append(
            RiskIndicator(
                code="CREDIT_SHORTFALL",
                name="Credit Shortfall vs Remaining Terms",
                severity=RiskSeverity.CRITICAL,
                category=RiskCategory.TIMELINE_COMPLETION,
                message=(
                    f"Required completion velocity ({required_velocity:.1f} credits/term) exceeds maximum standard "
                    f"term credit limit ({max_standard_credits:.1f}) across {remaining_terms} remaining term(s)."
                ),
                contributing_factors={
                    "remaining_credits_required": remaining_credits,
                    "remaining_terms_count": remaining_terms,
                    "required_credits_per_term": round(required_velocity, 2),
                    "max_standard_credits_per_term": max_standard_credits,
                    "max_possible_credits_at_standard_load": max_capacity,
                    "credit_deficit": max(0.0, credit_deficit),
                },
                source_records=source_records,
                actionable_recommendation=(
                    f"Extend graduation timeline by at least {int(remaining_credits / max_standard_credits) - remaining_terms + 1} "
                    f"additional term(s) or request formal credit overload approval from your academic advisor."
                ),
            )
        )

    return indicators


def evaluate_repeated_course_failures(
    student_record: StudentRecord,
) -> list[RiskIndicator]:
    """
    Identifies courses with multiple failed attempts (F, W, NC, etc.) without a subsequent passing grade.
    """
    indicators: list[RiskIndicator] = []
    failing_grades = {"F", "W", "NC", "U", "FAIL", "WF"}
    passing_grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "P", "S", "CR"}

    transcripts = list(
        TranscriptEntry.objects.filter(student_record=student_record)
        .select_related("course", "term")
        .order_by("term__start_date", "created_at")
    )

    # Group transcript entries by course
    attempts_by_course: dict[str, list[TranscriptEntry]] = {}
    for entry in transcripts:
        attempts_by_course.setdefault(str(entry.course_id), []).append(entry)

    for course_id, entries in attempts_by_course.items():
        failed_entries = [e for e in entries if (e.grade or "").upper() in failing_grades]
        passed_entries = [e for e in entries if (e.grade or "").upper() in passing_grades]

        if len(failed_entries) >= 2 and not passed_entries:
            course = failed_entries[0].course
            source_records = [
                SourceRecordReference(
                    entity_type="Course",
                    record_id=str(course.id),
                    display_name=f"{course.code} - {course.title}",
                ).to_dict(),
                SourceRecordReference(
                    entity_type="StudentRecord",
                    record_id=str(student_record.id),
                    display_name=student_record.student.username,
                ).to_dict(),
            ]

            indicators.append(
                RiskIndicator(
                    code="REPEATED_COURSE_FAILURE",
                    name="Repeated Course Failure",
                    severity=RiskSeverity.CRITICAL,
                    category=RiskCategory.ACADEMIC_STANDING,
                    message=(
                        f"Course '{course.code} - {course.title}' has been attempted {len(failed_entries)} times "
                        f"without a subsequent passing grade."
                    ),
                    contributing_factors={
                        "course_code": course.code,
                        "course_title": course.title,
                        "failed_attempt_count": len(failed_entries),
                        "grades_received": [e.grade for e in failed_entries],
                        "terms_attempted": [e.term.code for e in failed_entries if e.term],
                    },
                    source_records=source_records,
                    actionable_recommendation=(
                        f"Schedule an urgent advising consultation to discuss tutoring, prerequisite review, or course retake policies for {course.code}."
                    ),
                )
            )

    return indicators


def evaluate_prerequisite_bottlenecks(
    student_record: StudentRecord,
    bottleneck_threshold: int = 3,
) -> list[RiskIndicator]:
    """
    Identifies uncompleted courses that act as prerequisites for >= 3 downstream degree requirements.
    """
    indicators: list[RiskIndicator] = []
    pinned_cv = student_record.pinned_curriculum
    if not pinned_cv:
        return indicators

    passed_ids = get_passed_course_ids(student_record)

    # Find all prerequisite rules in pinned curriculum
    prereq_rules = list(
        PrerequisiteRule.objects.filter(curriculum_version=pinned_cv)
        .select_related("course")
    )

    # Map target courses back to their required prerequisite course codes
    # In rule_json, search for course codes required
    prereq_to_downstream_map: dict[str, list[str]] = {}

    for rule in prereq_rules:
        target_code = rule.course.code
        rule_json = rule.rule_json or {}
        # Simple extraction of course codes mentioned in rule AST
        referenced_codes = _extract_course_codes_from_ast(rule_json)
        for p_code in referenced_codes:
            prereq_to_downstream_map.setdefault(p_code, []).append(target_code)

    for p_code, downstream_codes in prereq_to_downstream_map.items():
        unique_downstream = sorted(list(set(downstream_codes)))
        if len(unique_downstream) >= bottleneck_threshold:
            # Check if student has passed this bottleneck course
            prereq_course = Course.objects.filter(
                institution=student_record.institution,
                code=p_code,
            ).first()

            if prereq_course and str(prereq_course.id) not in passed_ids:
                source_records = [
                    SourceRecordReference(
                        entity_type="Course",
                        record_id=str(prereq_course.id),
                        display_name=f"{prereq_course.code} - {prereq_course.title}",
                    ).to_dict(),
                    SourceRecordReference(
                        entity_type="StudentRecord",
                        record_id=str(student_record.id),
                        display_name=student_record.student.username,
                    ).to_dict(),
                ]

                indicators.append(
                    RiskIndicator(
                        code="PREREQUISITE_BOTTLENECK",
                        name="High-Impact Prerequisite Bottleneck",
                        severity=RiskSeverity.WARNING,
                        category=RiskCategory.PREREQUISITE,
                        message=(
                            f"Uncompleted course '{prereq_course.code}' is a critical prerequisite required by "
                            f"{len(unique_downstream)} downstream course(s): {', '.join(unique_downstream[:4])}."
                        ),
                        contributing_factors={
                            "bottleneck_course_code": prereq_course.code,
                            "downstream_course_count": len(unique_downstream),
                            "downstream_course_codes": unique_downstream,
                            "threshold": bottleneck_threshold,
                        },
                        source_records=source_records,
                        actionable_recommendation=(
                            f"Prioritize scheduling {prereq_course.code} in the next available term to avoid cascading scheduling delays."
                        ),
                    )
                )

    return indicators


def _extract_course_codes_from_ast(node: Any) -> set[str]:
    """Recursively extracts course codes from a prerequisite rule AST dictionary."""
    codes: set[str] = set()
    if isinstance(node, dict):
        if "course" in node and isinstance(node["course"], str):
            codes.add(node["course"])
        if "course_code" in node and isinstance(node["course_code"], str):
            codes.add(node["course_code"])
        for v in node.values():
            codes.update(_extract_course_codes_from_ast(v))
    elif isinstance(node, list):
        for item in node:
            codes.update(_extract_course_codes_from_ast(item))
    return codes
