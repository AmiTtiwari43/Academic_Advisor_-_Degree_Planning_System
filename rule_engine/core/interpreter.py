"""
Prerequisite Rule Interpreter (v1).
Pure Python. Deterministic AST visitor implementing Kleene three-valued logic.
Independent of Django. Zero external dependencies.
"""

from decimal import Decimal
from typing import Union

from rule_engine.core.context import (
    CompletedCourse,
    RepeatedCoursePolicy,
    RuleContext,
)
from rule_engine.core.result import EvaluationResult, EvaluationStatus, NodeResult
from rule_engine.core.validator import validate_rule_strict


class RuleInterpreter:
    """
    Interprets rule documents against student academic context using
    Kleene three-valued logic (SATISFIED, UNSATISFIED, INDETERMINATE).
    """

    def __init__(self, context: RuleContext):
        self.context = context
        self.grade_scale = context.grade_scale

    def evaluate(self, rule_doc: Union[dict, str]) -> EvaluationResult:
        """
        Validates rule syntax and evaluates student eligibility.
        """
        validate_rule_strict(rule_doc)

        if isinstance(rule_doc, str):
            import json

            data = json.loads(rule_doc)
        else:
            data = rule_doc

        rule_id = data.get("rule_id")
        curriculum_version_id = self.context.curriculum_version_id

        root_result = self._evaluate_node(data, path="$")

        # Collect deduplicated blocking reasons in deterministic order
        blocking_reasons: list[str] = []
        self._collect_blocking_reasons(root_result, blocking_reasons)

        eligible = root_result.status == EvaluationStatus.SATISFIED

        return EvaluationResult(
            eligible=eligible,
            status=root_result.status,
            node_results=root_result,
            blocking_reasons=tuple(blocking_reasons),
            rule_id=rule_id,
            curriculum_version_id=curriculum_version_id,
        )

    def _evaluate_node(self, node: dict, path: str) -> NodeResult:
        op_type = node["type"]

        if op_type == "course_completed":
            return self._eval_course_completed(node, path)
        elif op_type == "credits_completed":
            return self._eval_credits_completed(node, path)
        elif op_type == "cgpa_min":
            return self._eval_cgpa_min(node, path)
        elif op_type == "corequisite":
            return self._eval_corequisite(node, path)
        elif op_type == "anti_requisite":
            return self._eval_anti_requisite(node, path)
        elif op_type == "all_of":
            return self._eval_all_of(node, path)
        elif op_type == "any_of":
            return self._eval_any_of(node, path)
        else:
            raise ValueError(f"Unknown operator type: {op_type}")

    def _eval_course_completed(self, node: dict, path: str) -> NodeResult:
        course_code = node["course_code"].strip()
        min_grade = node.get("min_grade", "").strip() or None

        # 1. Check verified exemptions
        for ex in self.context.exemptions:
            if ex.verified and ex.course_code == course_code:
                return NodeResult(
                    node_path=path,
                    type="course_completed",
                    status=EvaluationStatus.SATISFIED,
                    explanation=f"Course {course_code} satisfied via verified exemption.",
                )

        # 2. Check verified transfer credits
        for tc in self.context.transfer_credits:
            if tc.verified and tc.course_code == course_code:
                return NodeResult(
                    node_path=path,
                    type="course_completed",
                    status=EvaluationStatus.SATISFIED,
                    explanation=f"Course {course_code} satisfied via verified transfer credit ({tc.credits} credits).",
                )

        # 3. Check completed courses
        matching_attempts = [
            cc for cc in self.context.completed_courses if cc.course_code == course_code
        ]

        if matching_attempts:
            chosen = self._select_course_attempt(matching_attempts)
            if min_grade:
                min_rank = self.grade_scale.get(min_grade)
                student_rank = self.grade_scale.get(chosen.grade)

                if min_rank is None or student_rank is None:
                    # Grade comparison missing from grade scale
                    reason = f"Grade scale comparison unavailable for grade '{chosen.grade}' vs required '{min_grade}'."
                    return NodeResult(
                        node_path=path,
                        type="course_completed",
                        status=EvaluationStatus.INDETERMINATE,
                        explanation=reason,
                        blocking_reasons=(reason,),
                    )

                if student_rank < min_rank:
                    reason = f"Course {course_code} completed with grade '{chosen.grade}', but minimum grade '{min_grade}' is required."
                    return NodeResult(
                        node_path=path,
                        type="course_completed",
                        status=EvaluationStatus.UNSATISFIED,
                        explanation=reason,
                        blocking_reasons=(reason,),
                    )

            return NodeResult(
                node_path=path,
                type="course_completed",
                status=EvaluationStatus.SATISFIED,
                explanation=f"Course {course_code} completed with grade '{chosen.grade}'.",
            )

        # 4. Check in-progress courses (does NOT satisfy course_completed)
        if course_code in self.context.in_progress_courses:
            reason = f"Course {course_code} is currently in progress; completed course required."
            return NodeResult(
                node_path=path,
                type="course_completed",
                status=EvaluationStatus.UNSATISFIED,
                explanation=reason,
                blocking_reasons=(reason,),
            )

        # 5. Not taken
        reason = f"Required course {course_code} has not been completed."
        return NodeResult(
            node_path=path,
            type="course_completed",
            status=EvaluationStatus.UNSATISFIED,
            explanation=reason,
            blocking_reasons=(reason,),
        )

    def _select_course_attempt(self, attempts: list[CompletedCourse]) -> CompletedCourse:
        if len(attempts) == 1:
            return attempts[0]

        if self.context.repeated_course_policy == RepeatedCoursePolicy.LATEST.value:
            # Sort by attempt_number descending
            return sorted(attempts, key=lambda a: a.attempt_number, reverse=True)[0]

        # Default: BEST_GRADE
        def get_rank(a: CompletedCourse) -> float:
            return self.grade_scale.get(a.grade, -1.0)

        return sorted(attempts, key=get_rank, reverse=True)[0]

    def _eval_credits_completed(self, node: dict, path: str) -> NodeResult:
        min_credits = Decimal(str(node["min_credits"]))
        category = node.get("category")

        if category:
            category = category.strip()
            # If category tracked in context
            if category in self.context.credits_by_category:
                earned = self.context.credits_by_category[category]
                if earned >= min_credits:
                    return NodeResult(
                        node_path=path,
                        type="credits_completed",
                        status=EvaluationStatus.SATISFIED,
                        explanation=f"Category '{category}' satisfied: {earned} credits earned (minimum {min_credits}).",
                    )
                else:
                    shortfall = min_credits - earned
                    reason = f"Insufficient credits in category '{category}': {earned} earned, {min_credits} required ({shortfall} remaining)."
                    return NodeResult(
                        node_path=path,
                        type="credits_completed",
                        status=EvaluationStatus.UNSATISFIED,
                        explanation=reason,
                        blocking_reasons=(reason,),
                    )
            else:
                # Category not present in credits_by_category
                if not self.context.credits_by_category and not self.context.completed_courses:
                    reason = f"Credit data not available for category '{category}'."
                    return NodeResult(
                        node_path=path,
                        type="credits_completed",
                        status=EvaluationStatus.INDETERMINATE,
                        explanation=reason,
                        blocking_reasons=(reason,),
                    )
                # Category simply has 0 earned
                reason = f"Insufficient credits in category '{category}': 0 earned, {min_credits} required."
                return NodeResult(
                    node_path=path,
                    type="credits_completed",
                    status=EvaluationStatus.UNSATISFIED,
                    explanation=reason,
                    blocking_reasons=(reason,),
                )

        # Total credits check
        earned = self.context.get_effective_total_credits()
        if earned >= min_credits:
            return NodeResult(
                node_path=path,
                type="credits_completed",
                status=EvaluationStatus.SATISFIED,
                explanation=f"Total credits satisfied: {earned} credits earned (minimum {min_credits}).",
            )
        else:
            shortfall = min_credits - earned
            reason = f"Insufficient total credits: {earned} earned, {min_credits} required ({shortfall} remaining)."
            return NodeResult(
                node_path=path,
                type="credits_completed",
                status=EvaluationStatus.UNSATISFIED,
                explanation=reason,
                blocking_reasons=(reason,),
            )

    def _eval_cgpa_min(self, node: dict, path: str) -> NodeResult:
        min_gpa = Decimal(str(node["value"]))

        if self.context.cgpa is None:
            reason = "Cumulative GPA is not available."
            return NodeResult(
                node_path=path,
                type="cgpa_min",
                status=EvaluationStatus.INDETERMINATE,
                explanation=reason,
                blocking_reasons=(reason,),
            )

        if self.context.cgpa >= min_gpa:
            return NodeResult(
                node_path=path,
                type="cgpa_min",
                status=EvaluationStatus.SATISFIED,
                explanation=f"Cumulative GPA {self.context.cgpa} meets minimum threshold of {min_gpa}.",
            )
        else:
            reason = f"Cumulative GPA {self.context.cgpa} is below required threshold of {min_gpa}."
            return NodeResult(
                node_path=path,
                type="cgpa_min",
                status=EvaluationStatus.UNSATISFIED,
                explanation=reason,
                blocking_reasons=(reason,),
            )

    def _eval_corequisite(self, node: dict, path: str) -> NodeResult:
        course_code = node["course_code"].strip()

        # 1. Planned for the same term
        if course_code in self.context.planned_same_term_courses:
            return NodeResult(
                node_path=path,
                type="corequisite",
                status=EvaluationStatus.SATISFIED,
                explanation=f"Corequisite {course_code} is planned for concurrent enrollment in the same term.",
            )

        # 2. Currently in progress
        if course_code in self.context.in_progress_courses:
            return NodeResult(
                node_path=path,
                type="corequisite",
                status=EvaluationStatus.SATISFIED,
                explanation=f"Corequisite {course_code} is currently in progress.",
            )

        # 3. Already completed, transferred, or exempt
        completed_codes = (
            {cc.course_code for cc in self.context.completed_courses}
            | {tc.course_code for tc in self.context.transfer_credits if tc.verified}
            | {ex.course_code for ex in self.context.exemptions if ex.verified}
        )

        if course_code in completed_codes:
            return NodeResult(
                node_path=path,
                type="corequisite",
                status=EvaluationStatus.SATISFIED,
                explanation=f"Corequisite {course_code} was previously completed.",
            )

        reason = f"Corequisite {course_code} is not scheduled, in progress, or completed."
        return NodeResult(
            node_path=path,
            type="corequisite",
            status=EvaluationStatus.UNSATISFIED,
            explanation=reason,
            blocking_reasons=(reason,),
        )

    def _eval_anti_requisite(self, node: dict, path: str) -> NodeResult:
        course_code = node["course_code"].strip()

        completed_codes = (
            {cc.course_code for cc in self.context.completed_courses}
            | {tc.course_code for tc in self.context.transfer_credits if tc.verified}
            | {ex.course_code for ex in self.context.exemptions if ex.verified}
        )

        # Unsatisfied if completed or in progress
        if course_code in completed_codes or course_code in self.context.in_progress_courses:
            reason = f"Anti-requisite {course_code} has already been completed or is currently in progress."
            return NodeResult(
                node_path=path,
                type="anti_requisite",
                status=EvaluationStatus.UNSATISFIED,
                explanation=reason,
                blocking_reasons=(reason,),
            )

        return NodeResult(
            node_path=path,
            type="anti_requisite",
            status=EvaluationStatus.SATISFIED,
            explanation=f"Anti-requisite {course_code} has not been taken.",
        )

    def _eval_all_of(self, node: dict, path: str) -> NodeResult:
        conditions = node["conditions"]
        child_results: list[NodeResult] = []

        for idx, cond in enumerate(conditions):
            child_path = f"{path}.conditions[{idx}]"
            res = self._evaluate_node(cond, child_path)
            child_results.append(res)

        # Kleene 3-valued logic for ALL_OF (AND):
        # - Any UNSATISFIED => UNSATISFIED
        # - Else if any INDETERMINATE => INDETERMINATE
        # - Else => SATISFIED
        has_unsatisfied = any(c.status == EvaluationStatus.UNSATISFIED for c in child_results)
        has_indeterminate = any(c.status == EvaluationStatus.INDETERMINATE for c in child_results)

        if has_unsatisfied:
            status = EvaluationStatus.UNSATISFIED
            explanation = "Not all conjunction conditions are satisfied."
        elif has_indeterminate:
            status = EvaluationStatus.INDETERMINATE
            explanation = (
                "One or more conjunction conditions could not be evaluated due to missing data."
            )
        else:
            status = EvaluationStatus.SATISFIED
            explanation = "All conjunction conditions are satisfied."

        return NodeResult(
            node_path=path,
            type="all_of",
            status=status,
            explanation=explanation,
            children=tuple(child_results),
        )

    def _eval_any_of(self, node: dict, path: str) -> NodeResult:
        conditions = node["conditions"]
        child_results: list[NodeResult] = []

        for idx, cond in enumerate(conditions):
            child_path = f"{path}.conditions[{idx}]"
            res = self._evaluate_node(cond, child_path)
            child_results.append(res)

        # Kleene 3-valued logic for ANY_OF (OR):
        # - Any SATISFIED => SATISFIED
        # - Else if all UNSATISFIED => UNSATISFIED
        # - Else => INDETERMINATE
        has_satisfied = any(c.status == EvaluationStatus.SATISFIED for c in child_results)
        all_unsatisfied = all(c.status == EvaluationStatus.UNSATISFIED for c in child_results)

        if has_satisfied:
            status = EvaluationStatus.SATISFIED
            explanation = "At least one disjunction alternative is satisfied."
        elif all_unsatisfied:
            status = EvaluationStatus.UNSATISFIED
            explanation = "None of the disjunction alternatives are satisfied."
        else:
            status = EvaluationStatus.INDETERMINATE
            explanation = "No disjunction alternative is satisfied, and some could not be evaluated due to missing data."

        return NodeResult(
            node_path=path,
            type="any_of",
            status=status,
            explanation=explanation,
            children=tuple(child_results),
        )

    def _collect_blocking_reasons(self, node: NodeResult, collected: list[str]) -> None:
        if node.status in (EvaluationStatus.UNSATISFIED, EvaluationStatus.INDETERMINATE):
            for reason in node.blocking_reasons:
                if reason not in collected:
                    collected.append(reason)
            for child in node.children:
                self._collect_blocking_reasons(child, collected)


def evaluate_rule(rule_doc: Union[dict, str], context: RuleContext) -> EvaluationResult:
    """Convenience functional evaluation entry point."""
    return RuleInterpreter(context).evaluate(rule_doc)
