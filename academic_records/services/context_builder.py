from decimal import Decimal
from typing import Any

from academic_records.models import (
    AcademicTerm,
    RepeatedCoursePolicy,
    StudentRecord,
    TranscriptEntryStatus,
    VerificationStatus,
)
from rule_engine.core.context import (
    DEFAULT_GRADE_SCALE,
    CompletedCourse,
    RuleContext,
)
from rule_engine.core.context import (
    Exemption as EngineExemption,
)
from rule_engine.core.context import (
    TransferCredit as EngineTransferCredit,
)


def build_rule_context(
    student_record: StudentRecord,
    as_of_term: AcademicTerm | None = None,
) -> RuleContext:
    """
    Builds a standalone, pure-Python RuleContext from official, verified student records.
    Strictly follows:
    1. Only VERIFIED and OFFICIAL_SEALED entries count.
    2. IN_PROGRESS entries populate `in_progress_courses` and NEVER count as completed/earned.
    3. Repeated course policy (BEST_GRADE, LATEST_GRADE, ALL_ATTEMPTS) is deterministically applied.
    4. Transfer credits and exemptions are validated.
    """
    entries_qs = student_record.transcript_entries.select_related(
        "course", "term"
    ).filter(
        verification_status__in=[
            VerificationStatus.VERIFIED,
            VerificationStatus.OFFICIAL_SEALED,
        ]
    )

    if as_of_term:
        entries_qs = entries_qs.filter(term__start_date__lte=as_of_term.start_date)

    entries = list(entries_qs)

    in_progress_codes: set[str] = set()
    completed_entries_by_course: dict[str, list[Any]] = {}

    for entry in entries:
        course_code = entry.course.code
        if entry.status == TranscriptEntryStatus.IN_PROGRESS:
            in_progress_codes.add(course_code)
        elif entry.status in (TranscriptEntryStatus.COMPLETED, TranscriptEntryStatus.FAILED):
            completed_entries_by_course.setdefault(course_code, []).append(entry)

    # Resolve repeated course policy
    effective_entries: list[Any] = []
    policy = student_record.repeated_course_policy

    for course_code, attempts in completed_entries_by_course.items():
        if len(attempts) == 1:
            effective_entries.append(attempts[0])
            continue

        if policy == RepeatedCoursePolicy.LATEST_GRADE:
            # Sort by attempt number descending or term start_date descending
            chosen = sorted(
                attempts,
                key=lambda a: (a.term.year, a.term.start_date, a.attempt_number),
                reverse=True,
            )[0]
            effective_entries.append(chosen)
        elif policy == RepeatedCoursePolicy.ALL_ATTEMPTS:
            effective_entries.extend(attempts)
        else:
            # Default: BEST_GRADE
            chosen = sorted(
                attempts,
                key=lambda a: (
                    DEFAULT_GRADE_SCALE.get(a.grade.upper(), -1.0),
                    a.attempt_number,
                ),
                reverse=True,
            )[0]
            effective_entries.append(chosen)

    # Build CompletedCourse dataclasses and compute CGPA
    completed_courses: list[CompletedCourse] = []
    total_quality_points = Decimal("0.00")
    total_gpa_credits = Decimal("0.00")
    total_earned_credits = Decimal("0.00")

    for entry in effective_entries:
        grade_str = entry.grade.strip().upper()
        credits_earned = entry.credits_earned
        credits_attempted = entry.credits_attempted

        completed_courses.append(
            CompletedCourse(
                course_code=entry.course.code,
                grade=grade_str,
                credits=credits_earned,
                status="completed" if entry.status == TranscriptEntryStatus.COMPLETED else "failed",
                attempt_number=entry.attempt_number,
                term=entry.term.code,
            )
        )

        total_earned_credits += credits_earned

        grade_val = DEFAULT_GRADE_SCALE.get(grade_str)
        if grade_val is not None and credits_attempted > Decimal("0.00"):
            total_quality_points += Decimal(str(grade_val)) * credits_attempted
            total_gpa_credits += credits_attempted

    cgpa = (
        round(total_quality_points / total_gpa_credits, 2)
        if total_gpa_credits > Decimal("0.00")
        else Decimal("0.00")
    )

    # Process Transfer Credits (only verified)
    transfer_credits_list: list[EngineTransferCredit] = []
    transfers_qs = student_record.transfer_credits.filter(is_verified=True)
    for tc in transfers_qs:
        transfer_credits_list.append(
            EngineTransferCredit(
                course_code=tc.course_code,
                credits=tc.credits,
                verified=True,
                grade=tc.grade,
            )
        )
        total_earned_credits += tc.credits

    # Process Exemptions
    exemptions_list: list[EngineExemption] = []
    exemptions_qs = student_record.exemptions.select_related("course").all()
    for ex in exemptions_qs:
        exemptions_list.append(
            EngineExemption(
                course_code=ex.course.code,
                verified=True,
            )
        )

    engine_policy = "latest" if policy == RepeatedCoursePolicy.LATEST_GRADE else "best_grade"

    return RuleContext(
        completed_courses=completed_courses,
        in_progress_courses=in_progress_codes,
        transfer_credits=transfer_credits_list,
        exemptions=exemptions_list,
        total_credits=total_earned_credits,
        cgpa=cgpa,
        curriculum_version_id=str(student_record.pinned_curriculum_id),
        repeated_course_policy=engine_policy,
    )


def compute_semester_gpas(student_record: StudentRecord) -> list[dict[str, Any]]:
    """
    Computes semester-by-semester SGPA (Semester Grade Point Average) and cumulative CGPA
    strictly on the standardized 10-point GPA scale.
    """
    entries = list(
        student_record.transcript_entries.select_related("course", "term")
        .filter(
            verification_status__in=[
                VerificationStatus.VERIFIED,
                VerificationStatus.OFFICIAL_SEALED,
            ]
        )
        .order_by("term__year", "term__start_date", "course__code")
    )

    terms_order: list[AcademicTerm] = []
    term_entries_map: dict[str, list[Any]] = {}

    for entry in entries:
        t = entry.term
        if t.code not in term_entries_map:
            terms_order.append(t)
            term_entries_map[t.code] = []
        term_entries_map[t.code].append(entry)

    semester_summaries: list[dict[str, Any]] = []
    cum_quality_points = Decimal("0.00")
    cum_gpa_credits = Decimal("0.00")
    cum_earned_credits = Decimal("0.00")

    for t in terms_order:
        term_entries = term_entries_map[t.code]
        term_attempted = Decimal("0.00")
        term_earned = Decimal("0.00")
        term_quality_points = Decimal("0.00")
        term_gpa_credits = Decimal("0.00")

        for e in term_entries:
            term_attempted += e.credits_attempted
            term_earned += e.credits_earned
            cum_earned_credits += e.credits_earned

            grade_val = DEFAULT_GRADE_SCALE.get(e.grade.strip().upper())
            if grade_val is not None and e.credits_attempted > Decimal("0.00"):
                qp = Decimal(str(grade_val)) * e.credits_attempted
                term_quality_points += qp
                term_gpa_credits += e.credits_attempted
                cum_quality_points += qp
                cum_gpa_credits += e.credits_attempted

        sgpa = (
            round(term_quality_points / term_gpa_credits, 2)
            if term_gpa_credits > Decimal("0.00")
            else Decimal("0.00")
        )
        cgpa_at_term = (
            round(cum_quality_points / cum_gpa_credits, 2)
            if cum_gpa_credits > Decimal("0.00")
            else Decimal("0.00")
        )

        semester_summaries.append(
            {
                "term_id": str(t.id),
                "term_code": t.code,
                "term_name": t.name,
                "year": t.year,
                "season": t.season,
                "credits_attempted": float(term_attempted),
                "credits_earned": float(term_earned),
                "sgpa": float(sgpa),
                "cumulative_cgpa": float(cgpa_at_term),
                "entries_count": len(term_entries),
            }
        )

    return semester_summaries

