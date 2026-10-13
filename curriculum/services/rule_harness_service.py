"""
Rule Test Harness Service.
Allows academic coordinators to test draft prerequisite rules against hypothetical student contexts
directly invoking the pure-Python Phase 03 rule engine without touching official database records.
"""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError

from rule_engine.core import (
    CompletedCourse,
    EvaluationResult,
    EvaluationStatus,
    Exemption,
    RepeatedCoursePolicy,
    RuleContext,
    RuleValidationError,
    TransferCredit,
    evaluate_rule,
    validate_rule_strict,
)


def _serialize_node_result(node: Any) -> dict[str, Any]:
    """Helper to serialize NodeResult tree."""
    return {
        "node_type": node.node_type,
        "path": node.path,
        "status": node.status.value,
        "is_satisfied": node.status.value == "SATISFIED",
        "reason": node.reason,
        "children": [_serialize_node_result(c) for c in node.children],
    }


def execute_rule_harness(
    rule_json: dict[str, Any], context_payload: dict[str, Any]
) -> dict[str, Any]:
    """
    Executes the pure-Python rule interpreter on the provided rule AST and context payload.
    Returns structured results for UI rendering.
    """
    # 1. AST Validation
    try:
        validate_rule_strict(rule_json)
    except (RuleValidationError, ValueError) as exc:
        raise ValidationError(f"Invalid prerequisite rule: {exc}") from exc

    # 2. Build Completed Courses & in-progress courses
    completed_courses = []
    in_progress_courses = set()
    for c in context_payload.get("completed_courses", []):
        code = str(c.get("course_code", "")).strip().upper()
        if c.get("is_in_progress", False):
            in_progress_courses.add(code)
        else:
            completed_courses.append(
                CompletedCourse(
                    course_code=code,
                    grade=str(c.get("grade", "A")),
                    credits=Decimal(str(c.get("credits", "3.0"))),
                    status=str(c.get("status", "completed")),
                    term=c.get("term"),
                )
            )

    transfer_credits = []
    for t in context_payload.get("transfer_credits", []):
        transfer_credits.append(
            TransferCredit(
                course_code=str(t.get("course_code", "")).strip().upper(),
                credits=Decimal(str(t.get("credits", "3.0"))),
                verified=bool(t.get("verified", True)),
                grade=str(t.get("grade", "CR")),
            )
        )

    exemptions = []
    for e in context_payload.get("exemptions", []):
        exemptions.append(
            Exemption(
                course_code=str(e.get("course_code", "")).strip().upper(),
                verified=bool(e.get("verified", True)),
            )
        )

    planned_same_term = {
        str(cc).strip().upper() for cc in context_payload.get("concurrent_courses", [])
    }
    in_prog_input = {
        str(ipc).strip().upper() for ipc in context_payload.get("in_progress_courses", [])
    }
    all_in_progress = in_progress_courses | in_prog_input

    cgpa_val = context_payload.get("cumulative_gpa", context_payload.get("cgpa"))
    cgpa = Decimal(str(cgpa_val)) if cgpa_val is not None else None

    tot_credits_val = context_payload.get("total_credits")
    total_credits = Decimal(str(tot_credits_val)) if tot_credits_val is not None else None

    credits_by_cat = {
        str(k).upper(): Decimal(str(v))
        for k, v in context_payload.get("category_credits", {}).items()
    }

    rep_policy_str = str(
        context_payload.get("repeated_policy", RepeatedCoursePolicy.BEST_GRADE.value)
    ).upper()
    rep_policy = (
        RepeatedCoursePolicy.LATEST.value
        if "LATEST" in rep_policy_str
        else RepeatedCoursePolicy.BEST_GRADE.value
    )

    ctx = RuleContext(
        completed_courses=completed_courses,
        in_progress_courses=all_in_progress,
        planned_same_term_courses=planned_same_term,
        transfer_credits=transfer_credits,
        exemptions=exemptions,
        credits_by_category=credits_by_cat,
        total_credits=total_credits,
        cgpa=cgpa,
        repeated_course_policy=rep_policy,
    )

    # 3. Pure-Python Engine Evaluation
    eval_result: EvaluationResult = evaluate_rule(rule_json, ctx)

    return {
        "status": eval_result.status.value,
        "eligible": eval_result.eligible,
        "is_satisfied": eval_result.status == EvaluationStatus.SATISFIED,
        "is_indeterminate": eval_result.status == EvaluationStatus.INDETERMINATE,
        "blocking_reasons": list(eval_result.blocking_reasons),
        "execution_tree": eval_result.node_results.to_dict(),
    }
