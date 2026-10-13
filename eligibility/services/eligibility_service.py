from dataclasses import asdict, dataclass
from typing import Any

from academic_records.models import AcademicTerm, StudentRecord
from academic_records.services.context_builder import build_rule_context
from curriculum.models import Course, PrerequisiteRule
from rule_engine.core import evaluate_rule


@dataclass(frozen=True)
class CourseEligibilityResult:
    course_id: str
    course_code: str
    course_title: str
    eligible: bool
    status: str
    is_satisfied: bool
    is_indeterminate: bool
    blocking_reasons: list[str]
    execution_tree: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_course_eligibility(
    student_record: StudentRecord,
    course: Course,
    as_of_term: AcademicTerm | None = None,
) -> CourseEligibilityResult:
    """
    Evaluates prerequisite eligibility for a specific course using the pure-Python
    rule engine and the student's pinned curriculum version.
    """
    rule = PrerequisiteRule.objects.filter(
        curriculum_version=student_record.pinned_curriculum,
        course=course,
    ).first()

    if not rule:
        # No prerequisite rule configured -> Course is freely eligible
        return CourseEligibilityResult(
            course_id=str(course.id),
            course_code=course.code,
            course_title=course.title,
            eligible=True,
            status="SATISFIED",
            is_satisfied=True,
            is_indeterminate=False,
            blocking_reasons=[],
            execution_tree=None,
        )

    context = build_rule_context(student_record, as_of_term)
    engine_result = evaluate_rule(rule.rule_json, context)

    is_satisfied = engine_result.eligible
    is_indeterminate = engine_result.status.value == "INDETERMINATE"

    return CourseEligibilityResult(
        course_id=str(course.id),
        course_code=course.code,
        course_title=course.title,
        eligible=engine_result.eligible,
        status=engine_result.status.value,
        is_satisfied=is_satisfied,
        is_indeterminate=is_indeterminate,
        blocking_reasons=list(engine_result.blocking_reasons),
        execution_tree=engine_result.to_dict(),
    )
