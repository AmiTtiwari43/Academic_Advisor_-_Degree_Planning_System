from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from academic_records.models import AcademicTerm
from academic_records.services.context_builder import build_rule_context
from curriculum.models import CourseOffering, PrerequisiteRule
from degree_audit.services.audit_service import run_degree_audit
from planning.models import Plan, PlanItem
from rule_engine.core import evaluate_rule
from rule_engine.core.context import CompletedCourse, RuleContext


@dataclass
class SimulationConstraint:
    code: str
    severity: str  # "HARD" or "WARNING"
    message: str
    course_code: str | None = None
    term_code: str | None = None
    term_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationCourseStatus:
    course_id: str
    course_code: str
    course_title: str
    credits: Decimal
    term_index: int
    term_code: str
    is_eligible: bool
    prerequisite_satisfied: bool
    corequisite_satisfied: bool
    offering_available: bool
    blocking_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationTermDetail:
    term_id: str
    term_code: str
    term_name: str
    term_index: int
    total_credits: Decimal
    is_credit_limit_exceeded: bool
    is_credit_minimum_met: bool
    courses: list[SimulationCourseStatus] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanSimulationReport:
    plan_id: str
    plan_name: str
    student_username: str
    curriculum_version_number: int
    total_planned_credits: Decimal
    total_cumulative_credits: Decimal
    is_valid_for_submission: bool
    hard_constraints: list[SimulationConstraint] = field(default_factory=list)
    warnings: list[SimulationConstraint] = field(default_factory=list)
    projected_graduation_term: str | None = None
    graduation_projection_reason: str | None = None
    audit_report: dict[str, Any] = field(default_factory=dict)
    terms: list[SimulationTermDetail] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_name": self.plan_name,
            "student_username": self.student_username,
            "curriculum_version_number": self.curriculum_version_number,
            "total_planned_credits": str(self.total_planned_credits),
            "total_cumulative_credits": str(self.total_cumulative_credits),
            "is_valid_for_submission": self.is_valid_for_submission,
            "hard_constraints": [c.to_dict() for c in self.hard_constraints],
            "warnings": [w.to_dict() for w in self.warnings],
            "projected_graduation_term": self.projected_graduation_term,
            "graduation_projection_reason": self.graduation_projection_reason,
            "audit_report": self.audit_report,
            "terms": [t.to_dict() for t in self.terms],
        }


# Credit limits
MIN_TERM_CREDITS = Decimal("12.00")
MAX_TERM_CREDITS = Decimal("18.00")
HARD_CEILING_TERM_CREDITS = Decimal("21.00")


def simulate_plan(
    plan: Plan,
    alternative_curriculum: Any = None,
) -> PlanSimulationReport:
    """
    Simulates a multi-semester degree plan against the student's academic history
    and curriculum version rules without mutating any database records.
    """
    target_curriculum = alternative_curriculum or plan.curriculum_version
    student_record = plan.student_record

    # 1. Fetch base verified completed courses from official record
    base_context = build_rule_context(student_record)
    simulated_completed: list[CompletedCourse] = list(base_context.completed_courses)
    simulated_total_credits = base_context.total_credits or Decimal("0.00")
    simulated_cgpa = base_context.cgpa or Decimal("3.00")

    # 2. Fetch all plan items sorted chronologically
    items_qs = (
        plan.items.select_related("course", "planned_term")
        .order_by("term_index", "position")
        .all()
    )
    items = list(items_qs)

    # Group items by (term_index, planned_term)
    term_dict: dict[tuple[int, str], list[PlanItem]] = {}
    term_objects: dict[str, AcademicTerm] = {}
    for it in items:
        key = (it.term_index, str(it.planned_term_id))
        term_dict.setdefault(key, []).append(it)
        term_objects[str(it.planned_term_id)] = it.planned_term

    sorted_keys = sorted(term_dict.keys(), key=lambda k: k[0])

    hard_constraints: list[SimulationConstraint] = []
    warnings: list[SimulationConstraint] = []
    term_details: list[SimulationTermDetail] = []

    total_planned_credits = Decimal("0.00")
    projected_grad_term: str | None = None
    projected_grad_reason: str | None = None

    # Track courses planned to check co-requisites within term
    for term_index, term_id in sorted_keys:
        planned_term = term_objects[term_id]
        term_items = term_dict[(term_index, term_id)]

        term_credits = sum(
            (Decimal(str(it.course.credits)) for it in term_items),
            Decimal("0.00"),
        )
        total_planned_credits += term_credits

        # Term load limits
        is_overload = term_credits > MAX_TERM_CREDITS
        is_hard_ceiling = term_credits > HARD_CEILING_TERM_CREDITS
        is_underload = term_credits < MIN_TERM_CREDITS and planned_term.season in ["FALL", "SPRING"]

        if is_hard_ceiling:
            hard_constraints.append(
                SimulationConstraint(
                    code="TERM_CREDIT_CEILING_EXCEEDED",
                    severity="HARD",
                    message=f"Term {term_index} ({planned_term.code}) exceeds maximum allowed ceiling of {HARD_CEILING_TERM_CREDITS} credits (planned: {term_credits} credits).",
                    term_code=planned_term.code,
                    term_index=term_index,
                )
            )
        elif is_overload:
            warnings.append(
                SimulationConstraint(
                    code="TERM_CREDIT_OVERLOAD",
                    severity="WARNING",
                    message=f"Term {term_index} ({planned_term.code}) exceeds recommended maximum of {MAX_TERM_CREDITS} credits (planned: {term_credits} credits).",
                    term_code=planned_term.code,
                    term_index=term_index,
                )
            )

        if is_underload:
            warnings.append(
                SimulationConstraint(
                    code="TERM_CREDIT_UNDERLOAD",
                    severity="WARNING",
                    message=f"Term {term_index} ({planned_term.code}) is below full-time minimum of {MIN_TERM_CREDITS} credits (planned: {term_credits} credits).",
                    term_code=planned_term.code,
                    term_index=term_index,
                )
            )

        # Context for evaluating prerequisites prior to this term
        current_prior_context = RuleContext(
            completed_courses=list(simulated_completed),
            in_progress_courses=set(),
            transfer_credits=list(base_context.transfer_credits),
            exemptions=list(base_context.exemptions),
            total_credits=simulated_total_credits,
            cgpa=simulated_cgpa,
            grade_scale=base_context.grade_scale,
            repeated_course_policy=base_context.repeated_course_policy,
        )

        term_course_statuses: list[SimulationCourseStatus] = []

        for it in term_items:
            crs = it.course
            blocking_reasons: list[str] = []
            prereq_satisfied = True
            coreq_satisfied = True
            offering_available = True

            # 1. Offering availability check (if institutional offerings exist for this term)
            offerings_exist = CourseOffering.objects.filter(academic_term=planned_term).exists()
            if offerings_exist:
                is_offered = CourseOffering.objects.filter(
                    academic_term=planned_term, course=crs
                ).exists()
                if not is_offered:
                    offering_available = False
                    warnings.append(
                        SimulationConstraint(
                            code="COURSE_NOT_OFFERED_IN_TERM",
                            severity="WARNING",
                            message=f"{crs.code} is not scheduled to be offered in {planned_term.code}.",
                            course_code=crs.code,
                            term_code=planned_term.code,
                            term_index=term_index,
                        )
                    )

            # 2. Prerequisite Rule Check using pure-Python engine
            rule = PrerequisiteRule.objects.filter(
                curriculum_version=target_curriculum,
                course=crs,
            ).first()

            if rule:
                engine_res = evaluate_rule(rule.rule_json, current_prior_context)
                if not engine_res.eligible:
                    prereq_satisfied = False
                    blocking_reasons.extend(engine_res.blocking_reasons)
                    hard_constraints.append(
                        SimulationConstraint(
                            code="PREREQUISITE_UNSATISFIED",
                            severity="HARD",
                            message=f"Prerequisite for {crs.code} unsatisfied prior to Term {term_index}: {'; '.join(engine_res.blocking_reasons)}",
                            course_code=crs.code,
                            term_code=planned_term.code,
                            term_index=term_index,
                        )
                    )

            is_eligible = prereq_satisfied and coreq_satisfied

            term_course_statuses.append(
                SimulationCourseStatus(
                    course_id=str(crs.id),
                    course_code=crs.code,
                    course_title=crs.title,
                    credits=crs.credits,
                    term_index=term_index,
                    term_code=planned_term.code,
                    is_eligible=is_eligible,
                    prerequisite_satisfied=prereq_satisfied,
                    corequisite_satisfied=coreq_satisfied,
                    offering_available=offering_available,
                    blocking_reasons=blocking_reasons,
                )
            )

        term_details.append(
            SimulationTermDetail(
                term_id=str(planned_term.id),
                term_code=planned_term.code,
                term_name=planned_term.name,
                term_index=term_index,
                total_credits=term_credits,
                is_credit_limit_exceeded=is_overload,
                is_credit_minimum_met=not is_underload,
                courses=term_course_statuses,
            )
        )

        # After evaluating this term, add completed planned courses into simulated history
        for it in term_items:
            simulated_completed.append(
                CompletedCourse(
                    course_code=it.course.code,
                    credits=Decimal(str(it.course.credits)),
                    grade="B",  # Projected grade threshold for simulation
                    status="completed",
                    term=planned_term.code,
                )
            )
        simulated_total_credits += term_credits

        # Check if graduation requirements are fulfilled at this term
        if projected_grad_term is None:
            interim_context = RuleContext(
                completed_courses=list(simulated_completed),
                in_progress_courses=set(),
                transfer_credits=list(base_context.transfer_credits),
                exemptions=list(base_context.exemptions),
                total_credits=simulated_total_credits,
                cgpa=simulated_cgpa,
                grade_scale=base_context.grade_scale,
                repeated_course_policy=base_context.repeated_course_policy,
            )
            interim_audit = run_degree_audit(
                student_record,
                simulated_context=interim_context,
                target_curriculum=target_curriculum,
                is_simulation=True,
            )
            if interim_audit.is_degree_satisfied:
                projected_grad_term = planned_term.code
                projected_grad_reason = (
                    f"All degree requirements ({interim_audit.total_credits_required} credits and "
                    f"{len(interim_audit.groups)} requirement groups) satisfied by end of {planned_term.code} (Term {term_index})."
                )

    # Final Cumulative Degree Audit after all planned terms
    final_context = RuleContext(
        completed_courses=list(simulated_completed),
        in_progress_courses=set(),
        transfer_credits=list(base_context.transfer_credits),
        exemptions=list(base_context.exemptions),
        total_credits=simulated_total_credits,
        cgpa=simulated_cgpa,
        grade_scale=base_context.grade_scale,
        repeated_course_policy=base_context.repeated_course_policy,
    )

    final_audit = run_degree_audit(
        student_record,
        simulated_context=final_context,
        target_curriculum=target_curriculum,
        is_simulation=True,
    )

    if projected_grad_term is None:
        unmet_cr = final_audit.remaining_credits_required
        unmet_groups = [g.name for g in final_audit.groups if not g.is_satisfied]
        projected_grad_reason = (
            f"Plan leaves {unmet_cr} credits and {len(unmet_groups)} requirement group(s) "
            f"({', '.join(unmet_groups)}) unsatisfied. Additional terms are required."
        )

    is_valid_for_submission = len(hard_constraints) == 0

    return PlanSimulationReport(
        plan_id=str(plan.id),
        plan_name=plan.name,
        student_username=student_record.student.username,
        curriculum_version_number=target_curriculum.version_number,
        total_planned_credits=total_planned_credits,
        total_cumulative_credits=simulated_total_credits,
        is_valid_for_submission=is_valid_for_submission,
        hard_constraints=hard_constraints,
        warnings=warnings,
        projected_graduation_term=projected_grad_term,
        graduation_projection_reason=projected_grad_reason,
        audit_report=final_audit.to_dict(),
        terms=term_details,
    )
