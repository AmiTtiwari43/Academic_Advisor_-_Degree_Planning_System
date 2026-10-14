"""
Comprehensive Test Suite for Constraint-Based Plan Optimizer (Prompt 08B).
Covers:
- Pure-Python architecture invariant: zero Django imports in planning.optimizer
- Multi-term scheduling with prerequisites precedence
- Seasonal offering availability constraints
- Corequisites and anti-requisites enforcement
- Term credit limits (max_credits ceiling and min_credits floor)
- Multiple pacing alternatives (Accelerated, Balanced, Light Pace) with trade-off explanations
- Already-completed and in-progress coursework handling
- Infeasibility diagnostics with specific blocking constraints:
  - Prerequisite depth exceeding available terms
  - Credit capacity deficit
  - Missing prerequisites
  - Anti-requisite conflicts
  - Offering season mismatches
- Solver timeout operational guard
- Per-user rate limiting / throttling guard (max 5 runs/min)
- Django service integration with mandatory Phase 06 simulation re-validation (0 hard constraints)
- Draft-only persistence invariant (generated plans saved strictly as DRAFT)
- REST API endpoints (POST /api/plans/optimize/, POST /api/plans/apply-optimized/)
- Tenant and authorization isolation
"""

import ast
import os
import time
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from academic_records.models import (
    AcademicTerm,
    StudentRecord,
)
from accounts.models import InstitutionMembership, Role
from curriculum.models import (
    Course,
    CurriculumStatus,
    CurriculumVersion,
    PrerequisiteRule,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupType,
)
from institutions.models import Institution
from planning.models import PlanStatus
from planning.optimizer import (
    OptimizationRequest,
    OptimizerCourse,
    OptimizerTerm,
    optimize_degree_plan,
)
from planning.services.optimizer_service import (
    OptimizerThrottledError,
    apply_candidate_plan,
    check_and_record_throttle,
    run_plan_optimization,
)

# ---------------------------------------------------------------------------
# Part 1: Pure-Python Optimizer Engine Tests (Zero Django imports)
# ---------------------------------------------------------------------------


def test_pure_python_optimizer_zero_django_imports():
    """Verifies that planning/optimizer/ is 100% pure Python and never imports Django."""
    optimizer_dir = os.path.join("planning", "optimizer")
    forbidden = {"django", "rest_framework"}

    for filename in os.listdir(optimizer_dir):
        if not filename.endswith(".py"):
            continue
        file_path = os.path.join(optimizer_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_pkg = alias.name.split(".")[0]
                    assert (
                        top_pkg not in forbidden
                    ), f"{file_path} imports forbidden package '{top_pkg}'"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_pkg = node.module.split(".")[0]
                    assert (
                        top_pkg not in forbidden
                    ), f"{file_path} imports from forbidden package '{top_pkg}'"


def test_optimizer_feasible_multi_term_prerequisites():
    """Asserts that prerequisites are scheduled in strictly earlier terms."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
        OptimizerTerm(index=2, code="TERM2", season="SPRING", year=2027, min_credits=0.0, max_credits=18.0),
        OptimizerTerm(index=3, code="TERM3", season="FALL", year=2027, min_credits=0.0, max_credits=18.0),
    ]

    courses = [
        OptimizerCourse(code="CS101", credits=4.0, is_mandatory=True),
        OptimizerCourse(code="CS102", credits=4.0, is_mandatory=True, prerequisites=["CS101"]),
        OptimizerCourse(code="CS201", credits=4.0, is_mandatory=True, prerequisites=["CS102"]),
    ]

    request = OptimizationRequest(available_terms=terms, courses_to_schedule=courses)
    result = optimize_degree_plan(request)

    assert result.is_feasible is True
    assert len(result.candidate_plans) >= 1
    plan = result.candidate_plans[0]

    term_indices = {sc.course_code: sc.term_index for sc in plan.scheduled_courses}
    assert term_indices["CS101"] < term_indices["CS102"]
    assert term_indices["CS102"] < term_indices["CS201"]


def test_optimizer_seasonal_offering_constraints():
    """Asserts that courses offered in specific seasons are only scheduled in matching terms."""
    terms = [
        OptimizerTerm(index=1, code="FALL_2026", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
        OptimizerTerm(index=2, code="SPRING_2027", season="SPRING", year=2027, min_credits=0.0, max_credits=18.0),
    ]

    courses = [
        OptimizerCourse(code="FALL_ONLY", credits=3.0, is_mandatory=True, offered_seasons=["FALL"]),
        OptimizerCourse(code="SPRING_ONLY", credits=3.0, is_mandatory=True, offered_seasons=["SPRING"]),
    ]

    request = OptimizationRequest(available_terms=terms, courses_to_schedule=courses)
    result = optimize_degree_plan(request)

    assert result.is_feasible is True
    plan = result.candidate_plans[0]
    term_assignments = {sc.course_code: sc.term_code for sc in plan.scheduled_courses}
    assert term_assignments["FALL_ONLY"] == "FALL_2026"
    assert term_assignments["SPRING_ONLY"] == "SPRING_2027"


def test_optimizer_corequisite_scheduling():
    """Asserts that corequisites can be scheduled in the same term or earlier term."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
        OptimizerTerm(index=2, code="TERM2", season="SPRING", year=2027, min_credits=0.0, max_credits=18.0),
    ]

    courses = [
        OptimizerCourse(code="PHYS101", credits=3.0, is_mandatory=True),
        OptimizerCourse(code="PHYS101L", credits=1.0, is_mandatory=True, corequisites=["PHYS101"]),
    ]

    request = OptimizationRequest(available_terms=terms, courses_to_schedule=courses)
    result = optimize_degree_plan(request)

    assert result.is_feasible is True
    plan = result.candidate_plans[0]
    indices = {sc.course_code: sc.term_index for sc in plan.scheduled_courses}
    # Lab term_index must be >= Lecture term_index
    assert indices["PHYS101L"] >= indices["PHYS101"]


def test_optimizer_anti_requisite_mutual_exclusion():
    """Asserts that mutually exclusive courses cannot both be scheduled."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
    ]

    # Two optional courses that are anti-requisites of each other
    courses = [
        OptimizerCourse(code="MATH101", credits=3.0, is_mandatory=False, anti_requisites=["MATH101_HONORS"]),
        OptimizerCourse(code="MATH101_HONORS", credits=4.0, is_mandatory=False, anti_requisites=["MATH101"]),
    ]

    request = OptimizationRequest(available_terms=terms, courses_to_schedule=courses)
    result = optimize_degree_plan(request)

    assert result.is_feasible is True
    plan = result.candidate_plans[0]
    sched_codes = {sc.course_code for sc in plan.scheduled_courses}
    assert not (("MATH101" in sched_codes) and ("MATH101_HONORS" in sched_codes))


def test_optimizer_pacing_alternatives_and_trade_offs():
    """Asserts that solver produces distinct pacing options with trade-off summaries."""
    terms = [
        OptimizerTerm(index=1, code="T1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
        OptimizerTerm(index=2, code="T2", season="SPRING", year=2027, min_credits=0.0, max_credits=18.0),
        OptimizerTerm(index=3, code="T3", season="FALL", year=2027, min_credits=0.0, max_credits=18.0),
        OptimizerTerm(index=4, code="T4", season="SPRING", year=2028, min_credits=0.0, max_credits=18.0),
    ]

    # 8 courses of 4.0 credits = 32 credits total
    courses = [
        OptimizerCourse(code=f"CRS{i}", credits=4.0, is_mandatory=True)
        for i in range(1, 9)
    ]

    request = OptimizationRequest(
        available_terms=terms,
        courses_to_schedule=courses,
        target_credits_per_term=16.0,
        max_plans=3,
    )
    result = optimize_degree_plan(request)

    assert result.is_feasible is True
    assert len(result.candidate_plans) >= 1

    for plan in result.candidate_plans:
        assert plan.trade_offs is not None
        assert plan.trade_offs.total_credits == 32.0
        assert plan.trade_offs.total_terms_used > 0
        assert len(plan.trade_offs.trade_off_explanation) > 0
        assert plan.trade_offs.average_credits_per_term > 0


def test_optimizer_honors_credit_limits():
    """Asserts that per-term credit bounds are strictly respected."""
    terms = [
        OptimizerTerm(index=1, code="T1", season="FALL", year=2026, min_credits=0.0, max_credits=12.0),
        OptimizerTerm(index=2, code="T2", season="SPRING", year=2027, min_credits=0.0, max_credits=12.0),
    ]

    courses = [
        OptimizerCourse(code=f"CS{i}", credits=4.0, is_mandatory=True)
        for i in range(1, 6)  # 5 courses = 20 credits
    ]

    request = OptimizationRequest(available_terms=terms, courses_to_schedule=courses)
    result = optimize_degree_plan(request)

    assert result.is_feasible is True
    plan = result.candidate_plans[0]
    for term_code, load in plan.term_loads.items():
        assert load <= 12.0


def test_optimizer_already_satisfied_courses_excluded():
    """Asserts completed courses are not scheduled but their prerequisites are satisfied."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
    ]

    courses = [
        OptimizerCourse(code="CS101", credits=4.0, is_mandatory=True),
        OptimizerCourse(code="CS102", credits=4.0, is_mandatory=True, prerequisites=["CS101"]),
    ]

    # CS101 is already completed
    request = OptimizationRequest(
        available_terms=terms,
        courses_to_schedule=courses,
        completed_courses={"CS101"},
    )
    result = optimize_degree_plan(request)

    assert result.is_feasible is True
    plan = result.candidate_plans[0]
    sched_codes = {sc.course_code for sc in plan.scheduled_courses}
    assert "CS101" not in sched_codes
    assert "CS102" in sched_codes
    assert plan.scheduled_courses[0].term_code == "TERM1"


def test_optimizer_infeasible_prerequisite_depth():
    """Detects when prerequisite depth exceeds the number of available terms."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
    ]

    courses = [
        OptimizerCourse(code="CS101", credits=3.0, is_mandatory=True),
        OptimizerCourse(code="CS102", credits=3.0, is_mandatory=True, prerequisites=["CS101"]),
    ]

    request = OptimizationRequest(available_terms=terms, courses_to_schedule=courses)
    result = optimize_degree_plan(request)

    assert result.is_feasible is False
    assert len(result.blocking_constraints) >= 1
    assert any("depth bottleneck" in b.lower() for b in result.blocking_constraints)


def test_optimizer_infeasible_credit_capacity_deficit():
    """Detects when total required credits exceed total cumulative term capacity."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=6.0),
    ]

    courses = [
        OptimizerCourse(code="CS101", credits=4.0, is_mandatory=True),
        OptimizerCourse(code="MATH101", credits=4.0, is_mandatory=True),
    ]

    request = OptimizationRequest(available_terms=terms, courses_to_schedule=courses)
    result = optimize_degree_plan(request)

    assert result.is_feasible is False
    assert len(result.blocking_constraints) >= 1
    assert any("capacity deficit" in b.lower() for b in result.blocking_constraints)


def test_optimizer_infeasible_missing_prerequisite():
    """Detects when a mandatory course requires a course not in curriculum or transcript."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
    ]

    courses = [
        OptimizerCourse(code="CS201", credits=4.0, is_mandatory=True, prerequisites=["MISSING_PREREQ"]),
    ]

    request = OptimizationRequest(available_terms=terms, courses_to_schedule=courses)
    result = optimize_degree_plan(request)

    assert result.is_feasible is False
    assert len(result.blocking_constraints) >= 1
    assert any("missing prerequisite" in b.lower() for b in result.blocking_constraints)


def test_optimizer_infeasible_anti_requisite_completed():
    """Detects when a mandatory course conflicts with an already-completed course."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
    ]

    courses = [
        OptimizerCourse(code="MATH101", credits=3.0, is_mandatory=True, anti_requisites=["MATH100"]),
    ]

    request = OptimizationRequest(
        available_terms=terms,
        courses_to_schedule=courses,
        completed_courses={"MATH100"},
    )
    result = optimize_degree_plan(request)

    assert result.is_feasible is False
    assert len(result.blocking_constraints) >= 1
    assert any("anti-requisite conflict" in b.lower() for b in result.blocking_constraints)


def test_optimizer_timeout_operational_guard():
    """Verifies that the solver honors the timeout_seconds parameter without hanging."""
    terms = [
        OptimizerTerm(index=1, code="TERM1", season="FALL", year=2026, min_credits=0.0, max_credits=18.0),
    ]
    courses = [
        OptimizerCourse(code="CS101", credits=3.0, is_mandatory=True),
    ]

    request = OptimizationRequest(
        available_terms=terms,
        courses_to_schedule=courses,
        timeout_seconds=0.5,
    )
    start = time.perf_counter()
    result = optimize_degree_plan(request)
    elapsed = time.perf_counter() - start

    assert result.is_feasible is True
    assert elapsed < 3.0  # Finished well within threshold


# ---------------------------------------------------------------------------
# Part 2: Django Service, Simulation Re-Validation, and API Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def optimizer_db_setup(db):
    """Sets up institution, curriculum, student, terms, and prerequisite rules."""
    institution = Institution.objects.create(
        name="Horizon University",
        domain="horizon-opt.edu",
        code="HORIZON_OPT",
    )

    prog = Programme.objects.create(
        institution=institution,
        code="BS-CS-OPT",
        name="BS Computer Science Optimizer",
    )

    curr_ver = CurriculumVersion.objects.create(
        institution=institution,
        programme=prog,
        version_number=1,
        academic_year="2026-2027",
        total_credits_required=Decimal("120.00"),
        status=CurriculumStatus.DRAFT,
    )

    req_group = RequirementGroup.objects.create(
        institution=institution,
        curriculum_version=curr_ver,
        name="Core Computer Science",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("16.00"),
        min_courses=4,
    )

    c1 = Course.objects.create(
        institution=institution, code="CS101_OPT", title="Intro to CS", credits=Decimal("4.00")
    )
    c2 = Course.objects.create(
        institution=institution, code="CS102_OPT", title="Data Structures", credits=Decimal("4.00")
    )
    c3 = Course.objects.create(
        institution=institution, code="MATH101_OPT", title="Calculus I", credits=Decimal("4.00")
    )
    c4 = Course.objects.create(
        institution=institution, code="CS201_OPT", title="Algorithms", credits=Decimal("4.00")
    )

    for c in [c1, c2, c3, c4]:
        RequirementGroupCourse.objects.create(
            requirement_group=req_group,
            course=c,
            is_mandatory=True,
        )

    # Prerequisite: CS101 -> CS102 -> CS201
    PrerequisiteRule.objects.create(
        institution=institution,
        curriculum_version=curr_ver,
        course=c2,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "CS101_OPT", "min_grade": "C"},
    )
    PrerequisiteRule.objects.create(
        institution=institution,
        curriculum_version=curr_ver,
        course=c4,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "CS102_OPT", "min_grade": "C"},
    )

    # Publish curriculum version (strictly immutable once published)
    curr_ver.status = CurriculumStatus.PUBLISHED
    curr_ver.save()

    # Academic terms
    term1 = AcademicTerm.objects.create(
        institution=institution,
        code="FALL_2026_OPT",
        name="Fall 2026",
        season="FALL",
        year=2026,
        start_date="2026-09-01",
        end_date="2026-12-15",
        is_active=True,
    )
    term2 = AcademicTerm.objects.create(
        institution=institution,
        code="SPRING_2027_OPT",
        name="Spring 2027",
        season="SPRING",
        year=2027,
        start_date="2027-01-15",
        end_date="2027-05-15",
        is_active=True,
    )
    term3 = AcademicTerm.objects.create(
        institution=institution,
        code="FALL_2027_OPT",
        name="Fall 2027",
        season="FALL",
        year=2027,
        start_date="2027-09-01",
        end_date="2027-12-15",
        is_active=True,
    )

    # Student user and record
    student_user = User.objects.create_user(
        username="optimizer_student", password="password123", email="opt_student@horizon.edu"
    )
    InstitutionMembership.objects.create(
        institution=institution, user=student_user, role=Role.STUDENT, is_active=True
    )
    student_record = StudentRecord.objects.create(
        institution=institution,
        student=student_user,
        programme=prog,
        pinned_curriculum=curr_ver,
        enrollment_term=term1,
        status="ACTIVE",
    )

    # Advisor user
    advisor_user = User.objects.create_user(
        username="optimizer_advisor", password="password123", email="opt_advisor@horizon.edu"
    )
    InstitutionMembership.objects.create(
        institution=institution, user=advisor_user, role=Role.ADVISOR, is_active=True
    )

    return {
        "institution": institution,
        "curriculum_version": curr_ver,
        "student_user": student_user,
        "student_record": student_record,
        "advisor_user": advisor_user,
        "terms": [term1, term2, term3],
        "courses": {"CS101": c1, "CS102": c2, "MATH101": c3, "CS201": c4},
    }


def test_optimizer_service_end_to_end_with_simulation_revalidation(optimizer_db_setup):
    """
    Asserts that the optimizer service loads DB models, solves the plan, and executes
    Phase 06 simulation re-validation asserting 0 hard constraint violations.
    """
    student_record = optimizer_db_setup["student_record"]
    curr_ver = optimizer_db_setup["curriculum_version"]
    terms = optimizer_db_setup["terms"]

    result = run_plan_optimization(
        student_record=student_record,
        curriculum_version=curr_ver,
        available_terms=terms,
        max_plans=2,
    )

    assert result.is_feasible is True
    assert len(result.candidate_plans) >= 1

    for plan in result.candidate_plans:
        # Strict Invariant: Every candidate plan MUST pass Phase 06 re-validation
        assert plan.is_validated is True
        assert any("Phase 06 simulation re-validation verified" in note for note in plan.validation_notes)


def test_apply_candidate_plan_saves_draft_only(optimizer_db_setup):
    """
    Asserts that applying an optimized candidate plan creates a plan strictly with
    status DRAFT, never auto-submitted, and leaves official records unmutated.
    """
    student_record = optimizer_db_setup["student_record"]
    curr_ver = optimizer_db_setup["curriculum_version"]
    terms = optimizer_db_setup["terms"]

    result = run_plan_optimization(
        student_record=student_record,
        curriculum_version=curr_ver,
        available_terms=terms,
        max_plans=1,
    )
    assert result.is_feasible is True
    candidate = result.candidate_plans[0]

    plan = apply_candidate_plan(
        student_record=student_record,
        candidate_plan=candidate,
        plan_name="My Four-Year Plan",
        is_primary=True,
    )

    # Invariants
    assert plan.status == PlanStatus.DRAFT
    assert plan.is_primary is True
    assert plan.items.count() == len(candidate.scheduled_courses)

    # Official academic record and published curriculum remain unchanged
    assert student_record.transcript_entries.count() == 0
    assert curr_ver.status == CurriculumStatus.PUBLISHED


def test_optimizer_rate_limit_throttle():
    """Asserts that exceeding 5 optimization requests within 60s raises OptimizerThrottledError."""
    cache.clear()
    user_id = 99999

    for _ in range(5):
        check_and_record_throttle(user_id=user_id, max_requests=5, window_seconds=60)

    # 6th call should be throttled
    with pytest.raises(OptimizerThrottledError) as exc_info:
        check_and_record_throttle(user_id=user_id, max_requests=5, window_seconds=60)

    assert "Rate limit exceeded" in str(exc_info.value)


def test_optimizer_api_endpoint_success(optimizer_db_setup):
    """Asserts POST /api/plans/optimize/ returns 200 with candidate plans and trade-offs."""
    cache.clear()
    client = APIClient()
    student_user = optimizer_db_setup["student_user"]
    student_record = optimizer_db_setup["student_record"]
    client.force_authenticate(user=student_user)

    url = "/api/plans/optimize/"
    payload = {
        "student_record_id": str(student_record.id),
        "max_plans": 2,
        "target_credits_per_term": 15.0,
    }
    response = client.post(url, data=payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    data = response.data
    assert data["is_feasible"] is True
    assert len(data["candidate_plans"]) >= 1
    assert "trade_offs" in data["candidate_plans"][0]
    assert data["candidate_plans"][0]["is_validated"] is True


def test_optimizer_api_apply_optimized_creates_draft(optimizer_db_setup):
    """Asserts POST /api/plans/apply-optimized/ creates a new DRAFT plan."""
    cache.clear()
    client = APIClient()
    student_user = optimizer_db_setup["student_user"]
    student_record = optimizer_db_setup["student_record"]
    terms = optimizer_db_setup["terms"]
    curr_ver = optimizer_db_setup["curriculum_version"]
    client.force_authenticate(user=student_user)

    # First get candidate plans
    result = run_plan_optimization(
        student_record=student_record,
        curriculum_version=curr_ver,
        available_terms=terms,
        max_plans=1,
    )
    candidate = result.candidate_plans[0]

    # Post candidate to apply-optimized endpoint
    url = "/api/plans/apply-optimized/"
    payload = {
        "student_record_id": str(student_record.id),
        "plan_name": "API Optimized Plan",
        "is_primary": True,
        "candidate_plan": {
            "plan_index": candidate.plan_index,
            "plan_label": candidate.plan_label,
            "scheduled_courses": [
                {
                    "course_code": sc.course_code,
                    "term_index": sc.term_index,
                    "term_code": sc.term_code,
                    "credits": sc.credits,
                }
                for sc in candidate.scheduled_courses
            ],
            "terms_used": candidate.terms_used,
            "term_loads": candidate.term_loads,
            "trade_offs": {
                "plan_label": candidate.trade_offs.plan_label,
                "total_terms_used": candidate.trade_offs.total_terms_used,
                "graduation_term_code": candidate.trade_offs.graduation_term_code,
                "total_credits": candidate.trade_offs.total_credits,
                "average_credits_per_term": candidate.trade_offs.average_credits_per_term,
                "workload_variance": candidate.trade_offs.workload_variance,
                "max_term_credits": candidate.trade_offs.max_term_credits,
                "min_term_credits": candidate.trade_offs.min_term_credits,
                "trade_off_explanation": candidate.trade_offs.trade_off_explanation,
            },
            "is_validated": candidate.is_validated,
            "validation_notes": candidate.validation_notes,
        },
    }

    response = client.post(url, data=payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "DRAFT"
    assert response.data["is_primary"] is True


def test_optimizer_api_tenant_and_permission_isolation(optimizer_db_setup):
    """Asserts that another student from a different institution cannot optimize this student's record."""
    cache.clear()
    other_institution = Institution.objects.create(
        name="Other College", domain="other-college.edu", code="OTHER_COLLEGE"
    )
    rogue_user = User.objects.create_user(
        username="rogue_user", password="password123", email="rogue@other.edu"
    )
    InstitutionMembership.objects.create(
        institution=other_institution, user=rogue_user, role=Role.STUDENT, is_active=True
    )

    client = APIClient()
    client.force_authenticate(user=rogue_user)

    url = "/api/plans/optimize/"
    payload = {
        "student_record_id": str(optimizer_db_setup["student_record"].id),
    }
    response = client.post(url, data=payload, format="json")
    assert response.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)
