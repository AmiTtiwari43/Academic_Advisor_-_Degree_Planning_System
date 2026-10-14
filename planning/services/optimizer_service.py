"""
Django integration service bridge for constraint-based degree plan optimization.
Bridges pure-Python CP-SAT solver with Django ORM, Simulation, and Degree Audit services.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Sequence

from django.core.cache import cache
from django.db import transaction

from academic_records.models import (
    AcademicTerm,
    StudentRecord,
    TranscriptEntryStatus,
    VerificationStatus,
)
from curriculum.graph.builder import _extract_edges_from_ast
from curriculum.graph.models import DependencyType
from curriculum.models import (
    Course,
    CourseOffering,
    CurriculumVersion,
    PrerequisiteRule,
    RequirementGroupCourse,
    RequirementGroupType,
)
from planning.models import Plan, PlanItem, PlanStatus
from planning.optimizer.models import (
    CandidatePlan,
    OptimizationRequest,
    OptimizationResult,
    OptimizerCourse,
    OptimizerTerm,
)
from planning.optimizer.solver import optimize_degree_plan
from planning.services.simulation_service import simulate_plan

logger = logging.getLogger(__name__)


class OptimizerThrottledError(Exception):
    """Raised when a user exceeds the allowed optimization request rate."""


def check_and_record_throttle(
    user_id: int | str,
    max_requests: int = 5,
    window_seconds: int = 60,
) -> None:
    """
    Enforces per-user sliding window throttle (default: max 5 requests per 60 seconds).
    """
    cache_key = f"optimizer_throttle_{user_id}"
    now = time.time()
    history = cache.get(cache_key, [])
    valid_history = [t for t in history if now - t < window_seconds]

    if len(valid_history) >= max_requests:
        raise OptimizerThrottledError(
            f"Rate limit exceeded: Maximum {max_requests} optimization runs per "
            f"{window_seconds} seconds allowed."
        )

    valid_history.append(now)
    cache.set(cache_key, valid_history, timeout=window_seconds + 10)


def run_plan_optimization(
    student_record: StudentRecord,
    curriculum_version: CurriculumVersion | None = None,
    available_terms: Sequence[AcademicTerm] | None = None,
    target_credits_per_term: float = 15.0,
    max_plans: int = 3,
    timeout_seconds: float = 5.0,
    enforce_min_credits: bool = True,
    user: Any = None,
) -> OptimizationResult:
    """
    Main entry point for degree plan optimization.
    Extracts curriculum and transcript context, runs CP-SAT solver, and performs
    mandatory Phase 06 simulation re-validation on all candidate plans.
    """
    if user is not None and getattr(user, "is_authenticated", False):
        check_and_record_throttle(user.id, max_requests=5, window_seconds=60)

    target_curriculum = (
        curriculum_version
        or getattr(student_record, "pinned_curriculum", None)
        or getattr(student_record, "curriculum_version", None)
    )
    if not target_curriculum:
        return OptimizationResult(
            is_feasible=False,
            blocking_constraints=["Student record has no assigned curriculum version."],
            solver_status="NO_CURRICULUM",
        )

    institution = student_record.institution

    # 1. Fetch available terms
    if available_terms is None:
        terms_qs = AcademicTerm.objects.filter(
            institution=institution,
            is_active=True,
        ).order_by("year", "start_date")
        terms_list = list(terms_qs)
    else:
        terms_list = list(available_terms)

    if not terms_list:
        return OptimizationResult(
            is_feasible=False,
            blocking_constraints=["No active academic terms found for this institution."],
            solver_status="NO_TERMS",
        )

    term_db_map = {t.code.strip().upper(): t for t in terms_list}

    optimizer_terms = [
        OptimizerTerm(
            index=idx + 1,
            code=t.code,
            name=t.name,
            season=t.season,
            year=t.year,
            min_credits=12.0 if t.season.upper() in ("FALL", "SPRING") else 0.0,
            max_credits=18.0,
        )
        for idx, t in enumerate(terms_list)
    ]

    # 2. Extract completed and in-progress coursework from transcript
    completed_codes = set(
        student_record.transcript_entries.filter(
            status=TranscriptEntryStatus.COMPLETED,
            verification_status=VerificationStatus.VERIFIED,
        ).values_list("course__code", flat=True)
    )
    in_progress_codes = set(
        student_record.transcript_entries.filter(
            status=TranscriptEntryStatus.IN_PROGRESS
        ).values_list("course__code", flat=True)
    )

    # 3. Extract required coursework from curriculum version
    group_courses = (
        RequirementGroupCourse.objects.filter(
            requirement_group__curriculum_version=target_curriculum
        )
        .select_related("course", "requirement_group")
        .all()
    )

    course_db_map: dict[str, Course] = {}
    optimizer_courses: list[OptimizerCourse] = []
    seen_course_codes: set[str] = set()

    for rgc in group_courses:
        c = rgc.course
        code_upper = c.code.strip().upper()
        course_db_map[code_upper] = c

        if code_upper in seen_course_codes:
            continue
        seen_course_codes.add(code_upper)

        is_mandatory = (
            rgc.is_mandatory
            or rgc.requirement_group.group_type == RequirementGroupType.MANDATORY
        )

        # Prerequisite / corequisite / anti-requisite AST extraction
        prereqs: list[str] = []
        coreqs: list[str] = []
        antireqs: list[str] = []

        rule = PrerequisiteRule.objects.filter(
            curriculum_version=target_curriculum,
            course=c,
        ).first()

        if rule and rule.rule_json:
            edges = _extract_edges_from_ast(code_upper, rule.rule_json)
            for edge in edges:
                if edge.dependency_type == DependencyType.PREREQUISITE:
                    prereqs.append(edge.prerequisite)
                elif edge.dependency_type == DependencyType.COREQUISITE:
                    coreqs.append(edge.prerequisite)
                elif edge.dependency_type == DependencyType.ANTI_REQUISITE:
                    antireqs.append(edge.prerequisite)

        # Offerings season detection
        offerings = CourseOffering.objects.filter(course=c, is_offered=True)
        if offerings.exists():
            seasons = list({o.academic_term.strip().upper() for o in offerings})
        else:
            seasons = ["FALL", "SPRING", "SUMMER"]

        optimizer_courses.append(
            OptimizerCourse(
                code=code_upper,
                title=c.title,
                credits=float(c.credits),
                is_mandatory=is_mandatory,
                prerequisites=prereqs,
                corequisites=coreqs,
                anti_requisites=antireqs,
                offered_seasons=seasons,
            )
        )

    # 4. Build optimization request
    opt_request = OptimizationRequest(
        available_terms=optimizer_terms,
        courses_to_schedule=optimizer_courses,
        completed_courses=completed_codes,
        in_progress_courses=in_progress_codes,
        target_credits_per_term=target_credits_per_term,
        enforce_min_credits=enforce_min_credits,
        max_plans=max_plans,
        timeout_seconds=timeout_seconds,
    )

    # 5. Execute solver
    opt_result = optimize_degree_plan(opt_request)

    # 6. Mandatory Re-Validation against Phase 06 Simulation & Phase 05 Degree Audit
    if opt_result.is_feasible and opt_result.candidate_plans:
        for candidate in opt_result.candidate_plans:
            _revalidate_candidate_plan(
                candidate=candidate,
                student_record=student_record,
                curriculum_version=target_curriculum,
                course_db_map=course_db_map,
                term_db_map=term_db_map,
            )

    return opt_result


def _revalidate_candidate_plan(
    candidate: CandidatePlan,
    student_record: StudentRecord,
    curriculum_version: CurriculumVersion,
    course_db_map: dict[str, Course],
    term_db_map: dict[str, AcademicTerm],
) -> None:
    """
    Performs transactional simulation of a candidate plan without persisting records.
    Asserts 0 hard constraints and checks degree audit results.
    """
    institution = student_record.institution

    try:
        with transaction.atomic():
            temp_plan = Plan.objects.create(
                institution=institution,
                student_record=student_record,
                curriculum_version=curriculum_version,
                name=f"Transient Validation Plan ({candidate.plan_label})",
                status=PlanStatus.DRAFT,
            )

            for idx, sc in enumerate(candidate.scheduled_courses):
                course_obj = course_db_map.get(sc.course_code.upper())
                term_obj = term_db_map.get(sc.term_code.upper())
                if course_obj and term_obj:
                    PlanItem.objects.create(
                        institution=institution,
                        plan=temp_plan,
                        course=course_obj,
                        planned_term=term_obj,
                        term_index=sc.term_index,
                        position=idx,
                    )

            # Execute simulation (includes Phase 05 degree audit)
            sim_report = simulate_plan(
                plan=temp_plan,
                alternative_curriculum=curriculum_version,
            )

            if len(sim_report.hard_constraints) == 0:
                candidate.is_validated = True
                grad_term = sim_report.projected_graduation_term or "N/A"
                candidate.validation_notes.append(
                    f"Phase 06 simulation re-validation verified (0 hard constraints). "
                    f"Audit projection: {grad_term}."
                )
            else:
                candidate.is_validated = False
                for hc in sim_report.hard_constraints:
                    candidate.validation_notes.append(f"Hard constraint: {hc.message}")

            # Rollback to keep database completely pristine
            transaction.set_rollback(True)

    except Exception as exc:
        logger.warning(
            "Validation execution error during plan optimization re-validation: %s", exc
        )
        candidate.is_validated = False
        candidate.validation_notes.append(f"Simulation error during re-validation: {exc}")


def apply_candidate_plan(
    student_record: StudentRecord,
    candidate_plan: CandidatePlan,
    plan_name: str = "Optimized Academic Plan",
    curriculum_version: CurriculumVersion | None = None,
    is_primary: bool = False,
    user: Any = None,
) -> Plan:
    """
    Saves an approved candidate plan into the database.
    INVARIANT: Plans generated by the optimizer are saved strictly as DRAFT.
    Never auto-submitted.
    """
    target_curriculum = (
        curriculum_version
        or getattr(student_record, "pinned_curriculum", None)
        or getattr(student_record, "curriculum_version", None)
    )
    institution = student_record.institution

    # Build DB lookups
    course_codes = [sc.course_code.upper() for sc in candidate_plan.scheduled_courses]
    term_codes = [sc.term_code.upper() for sc in candidate_plan.scheduled_courses]

    course_map = {
        c.code.upper(): c
        for c in Course.objects.filter(institution=institution, code__in=course_codes)
    }
    term_map = {
        t.code.upper(): t
        for t in AcademicTerm.objects.filter(institution=institution, code__in=term_codes)
    }

    with transaction.atomic():
        if is_primary:
            Plan.objects.filter(
                student_record=student_record,
                is_primary=True,
            ).update(is_primary=False)

        plan = Plan.objects.create(
            institution=institution,
            student_record=student_record,
            curriculum_version=target_curriculum,
            name=f"{plan_name} ({candidate_plan.plan_label})",
            is_primary=is_primary,
            status=PlanStatus.DRAFT,  # Strict invariant: DRAFT only
        )

        for idx, sc in enumerate(candidate_plan.scheduled_courses):
            course_obj = course_map.get(sc.course_code.upper())
            term_obj = term_map.get(sc.term_code.upper())
            if not course_obj:
                raise ValueError(f"Course {sc.course_code} not found in database.")
            if not term_obj:
                raise ValueError(f"Academic term {sc.term_code} not found in database.")

            PlanItem.objects.create(
                institution=institution,
                plan=plan,
                course=course_obj,
                planned_term=term_obj,
                term_index=sc.term_index,
                position=idx,
                notes=f"Auto-scheduled by optimizer ({candidate_plan.plan_label} pace)",
            )

    return plan
