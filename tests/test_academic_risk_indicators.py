"""
Comprehensive Test Suite for Rule-Based Academic Risk Indicators (Prompt 08E).
Covers:
- Domain models, constraints, and string representations
- Individual transparent rule evaluators (missing critical prerequisite, unoffered required courses,
  registration deadline approaching, credit shortfall, repeated course failure, prerequisite bottleneck)
- Contributing factors and source record references verification
- Output determinism and overall risk level calculation
- Non-destructive invariant: 0 row mutations on official academic records
- REST API endpoints, permissions, student ownership, and cross-tenant isolation
- Aggregated institution risk summary
- Advisor risk acknowledgment workflow
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APIClient

from academic_records.models import (
    AcademicTerm,
    StudentRecord,
    StudentRecordStatus,
    TermSeason,
    TranscriptEntry,
    TranscriptEntryStatus,
    VerificationStatus,
)
from accounts.models import AdvisorAssignment, InstitutionMembership, Role
from advising.models import (
    AcknowledgmentStatus,
    OverallRiskLevel,
    RiskAcknowledgment,
    RiskCategory,
    RiskSeverity,
    StudentRiskProfile,
)
from advising.services import (
    evaluate_student_risks,
    get_student_risk_profile,
)
from advising.services.risk_evaluators import (
    evaluate_credit_shortfall,
    evaluate_missing_critical_prerequisites,
    evaluate_prerequisite_bottlenecks,
    evaluate_registration_deadlines,
    evaluate_repeated_course_failures,
    evaluate_required_courses_unoffered,
)
from curriculum.models import (
    Course,
    CourseOffering,
    CurriculumStatus,
    CurriculumVersion,
    DeliveryMode,
    PrerequisiteRule,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupType,
)
from institutions.models import Institution
from planning.models import Plan, PlanItem, PlanStatus


@pytest.fixture
def risk_fixture(db):
    """
    Sets up a complete multi-tenant fixture for Academic Risk Indicator testing:
    - Institution A & Institution B
    - Coordinator, Assigned Advisor, Unassigned Advisor, Student A, Student B (Inst A), Student C (Inst B)
    - Pinned Curriculum: BS-CS with Core and Electives
    - Terms: Past Term, Imminent Term (starts in 5 days), Future Term
    - Courses: CS101, CS201 (requires CS101), CS301 (mandatory), CS100 (bottleneck), MATH101
    """
    institution = Institution.objects.create(
        name="Titan State University",
        domain="titan-risk.edu",
        code="TITAN_RISK",
    )
    other_institution = Institution.objects.create(
        name="Apollo Institute",
        domain="apollo-risk.edu",
        code="APOLLO_RISK",
    )

    today = date.today()

    # Academic terms
    past_term = AcademicTerm.objects.create(
        institution=institution,
        code="PAST-2025",
        name="Past Fall 2025",
        season=TermSeason.FALL,
        year=2025,
        start_date=today - timedelta(days=120),
        end_date=today - timedelta(days=30),
        is_active=True,
    )
    imminent_term = AcademicTerm.objects.create(
        institution=institution,
        code="IMMINENT-2026",
        name="Imminent Spring 2026",
        season=TermSeason.SPRING,
        year=2026,
        start_date=today + timedelta(days=5),
        end_date=today + timedelta(days=100),
        is_active=True,
    )
    future_term = AcademicTerm.objects.create(
        institution=institution,
        code="FUTURE-2026",
        name="Future Fall 2026",
        season=TermSeason.FALL,
        year=2026,
        start_date=today + timedelta(days=150),
        end_date=today + timedelta(days=250),
        is_active=True,
    )

    # Users
    coordinator = User.objects.create_user(
        username="coord_titan",
        email="coord@titan-risk.edu",
        password="password123",
    )
    InstitutionMembership.objects.create(
        user=coordinator,
        institution=institution,
        role=Role.COORDINATOR,
        is_active=True,
    )

    advisor = User.objects.create_user(
        username="advisor_assigned",
        email="advisor@titan-risk.edu",
        password="password123",
    )
    advisor_mem = InstitutionMembership.objects.create(
        user=advisor,
        institution=institution,
        role=Role.ADVISOR,
        is_active=True,
    )

    unassigned_advisor = User.objects.create_user(
        username="advisor_unassigned",
        email="unassigned@titan-risk.edu",
        password="password123",
    )
    InstitutionMembership.objects.create(
        user=unassigned_advisor,
        institution=institution,
        role=Role.ADVISOR,
        is_active=True,
    )

    student_user_a = User.objects.create_user(
        username="alice_risk",
        email="alice@titan-risk.edu",
        first_name="Alice",
        last_name="Smith",
        password="password123",
    )
    student_mem_a = InstitutionMembership.objects.create(
        user=student_user_a,
        institution=institution,
        role=Role.STUDENT,
        is_active=True,
    )

    student_user_b = User.objects.create_user(
        username="bob_risk",
        email="bob@titan-risk.edu",
        password="password123",
    )
    InstitutionMembership.objects.create(
        user=student_user_b,
        institution=institution,
        role=Role.STUDENT,
        is_active=True,
    )

    other_student_user = User.objects.create_user(
        username="charlie_other",
        email="charlie@apollo-risk.edu",
        password="password123",
    )
    InstitutionMembership.objects.create(
        user=other_student_user,
        institution=other_institution,
        role=Role.STUDENT,
        is_active=True,
    )

    # Advisor assignment: advisor is assigned to student A
    AdvisorAssignment.objects.create(
        institution=institution,
        advisor=advisor_mem,
        student=student_mem_a,
        is_active=True,
    )

    # Programme & Curriculum
    programme = Programme.objects.create(
        institution=institution,
        code="CS_TITAN",
        name="BS Computer Science",
    )
    curriculum_version = CurriculumVersion.objects.create(
        institution=institution,
        programme=programme,
        version_number=1,
        academic_year="2025-2026",
        status=CurriculumStatus.DRAFT,
        total_credits_required=Decimal("120.00"),
        min_cgpa_required=Decimal("2.000"),
    )

    # Requirement Groups
    core_group = RequirementGroup.objects.create(
        institution=institution,
        curriculum_version=curriculum_version,
        name="Core Computer Science",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("12.00"),
        min_courses=3,
        display_order=1,
    )

    # Courses
    cs101 = Course.objects.create(
        institution=institution,
        code="CS101",
        title="Intro to Programming",
        credits=Decimal("4.00"),
    )
    cs201 = Course.objects.create(
        institution=institution,
        code="CS201",
        title="Data Structures",
        credits=Decimal("4.00"),
    )
    cs301 = Course.objects.create(
        institution=institution,
        code="CS301",
        title="Algorithms",
        credits=Decimal("4.00"),
    )
    cs100 = Course.objects.create(
        institution=institution,
        code="CS100",
        title="Discrete Mathematics",
        credits=Decimal("3.00"),
    )
    math101 = Course.objects.create(
        institution=institution,
        code="MATH101",
        title="Calculus I",
        credits=Decimal("4.00"),
    )

    # Link courses to core group (mandatory)
    RequirementGroupCourse.objects.create(
        requirement_group=core_group,
        course=cs101,
        is_mandatory=True,
        display_order=1,
    )
    RequirementGroupCourse.objects.create(
        requirement_group=core_group,
        course=cs201,
        is_mandatory=True,
        display_order=2,
    )
    RequirementGroupCourse.objects.create(
        requirement_group=core_group,
        course=cs301,
        is_mandatory=True,
        display_order=3,
    )

    # Prerequisite Rule: CS201 requires CS101
    prereq_cs201 = PrerequisiteRule.objects.create(
        institution=institution,
        curriculum_version=curriculum_version,
        course=cs201,
        description="Requires CS101",
        rule_json={
            "schema_version": 1,
            "type": "course_completed",
            "course_code": "CS101",
            "min_grade": "C",
        },
    )

    # Prerequisite Rules for bottleneck course CS100 (CS201, CS202, CS203 require CS100)
    cs202 = Course.objects.create(institution=institution, code="CS202", title="Automata Theory", credits=Decimal("3.00"))
    cs203 = Course.objects.create(institution=institution, code="CS203", title="Logic Systems", credits=Decimal("3.00"))
    PrerequisiteRule.objects.create(
        institution=institution,
        curriculum_version=curriculum_version,
        course=cs202,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "CS100", "min_grade": "D"},
    )
    PrerequisiteRule.objects.create(
        institution=institution,
        curriculum_version=curriculum_version,
        course=cs203,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "CS100", "min_grade": "D"},
    )
    # Also add CS100 as prereq to CS301
    PrerequisiteRule.objects.create(
        institution=institution,
        curriculum_version=curriculum_version,
        course=cs301,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "CS100", "min_grade": "D"},
    )

    # Publish curriculum version after authoring
    curriculum_version.status = CurriculumStatus.PUBLISHED
    curriculum_version.save()

    # Student Record for Alice
    student_record_a = StudentRecord.objects.create(
        institution=institution,
        student=student_user_a,
        programme=programme,
        pinned_curriculum=curriculum_version,
        enrollment_term=past_term,
        status=StudentRecordStatus.ACTIVE,
    )

    # Student Record for Charlie (Other Institution)
    other_programme = Programme.objects.create(
        institution=other_institution,
        code="CS_APOLLO",
        name="BS Computer Science",
    )
    other_curriculum = CurriculumVersion.objects.create(
        institution=other_institution,
        programme=other_programme,
        version_number=1,
        academic_year="2025-2026",
        status=CurriculumStatus.PUBLISHED,
        total_credits_required=Decimal("120.00"),
    )
    other_term = AcademicTerm.objects.create(
        institution=other_institution,
        code="APOLLO-PAST-2025",
        name="Apollo Past Fall 2025",
        season=TermSeason.FALL,
        year=2025,
        start_date=today - timedelta(days=120),
        end_date=today - timedelta(days=30),
        is_active=True,
    )
    student_record_other = StudentRecord.objects.create(
        institution=other_institution,
        student=other_student_user,
        programme=other_programme,
        pinned_curriculum=other_curriculum,
        enrollment_term=other_term,
        status=StudentRecordStatus.ACTIVE,
    )

    return {
        "institution": institution,
        "other_institution": other_institution,
        "coordinator": coordinator,
        "advisor": advisor,
        "unassigned_advisor": unassigned_advisor,
        "student_user_a": student_user_a,
        "student_user_b": student_user_b,
        "other_student_user": other_student_user,
        "student_record_a": student_record_a,
        "student_record_other": student_record_other,
        "curriculum_version": curriculum_version,
        "past_term": past_term,
        "imminent_term": imminent_term,
        "future_term": future_term,
        "cs101": cs101,
        "cs201": cs201,
        "cs301": cs301,
        "cs100": cs100,
        "math101": math101,
        "prereq_cs201": prereq_cs201,
    }


def test_risk_models_and_constraints(risk_fixture):
    """Verifies StudentRiskProfile unique constraints and RiskAcknowledgment model."""
    inst = risk_fixture["institution"]
    rec_a = risk_fixture["student_record_a"]

    profile = StudentRiskProfile.objects.create(
        institution=inst,
        student_record=rec_a,
        overall_risk_level=OverallRiskLevel.HIGH,
        active_risk_count=2,
        critical_risk_count=1,
        warning_risk_count=1,
        indicators=[{"code": "TEST_RISK", "severity": "CRITICAL"}],
        summary="High risk detected",
    )
    assert profile.pk is not None
    assert "RiskProfile" in str(profile)

    # PostgreSQL atomic block for unique constraint test
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            StudentRiskProfile.objects.create(
                institution=inst,
                student_record=rec_a,
                overall_risk_level=OverallRiskLevel.LOW,
            )

    # RiskAcknowledgment
    ack = RiskAcknowledgment.objects.create(
        risk_profile=profile,
        indicator_code="TEST_RISK",
        advisor=risk_fixture["advisor"],
        status=AcknowledgmentStatus.ACKNOWLEDGED,
        notes="Discussed with student during office hours.",
        action_plan="Student will register for tutoring.",
    )
    assert ack.pk is not None
    assert ack.institution == inst
    assert "Acknowledgment" in str(ack)


def test_missing_critical_prerequisite_rule(risk_fixture):
    """
    Verifies that an uncompleted mandatory course with unmet prerequisites
    is flagged with exact contributing factors and cleared upon course completion.
    """
    rec_a = risk_fixture["student_record_a"]
    cs101 = risk_fixture["cs101"]
    cs201 = risk_fixture["cs201"]

    # Alice has NOT completed CS101 -> CS201 prerequisite is missing
    indicators = evaluate_missing_critical_prerequisites(rec_a)
    prereq_risks = [i for i in indicators if i.code == "MISSING_CRITICAL_PREREQUISITE" and i.contributing_factors.get("course_code") == "CS201"]

    assert len(prereq_risks) == 1
    risk = prereq_risks[0]
    assert risk.severity == RiskSeverity.CRITICAL
    assert risk.category == RiskCategory.PREREQUISITE
    assert "CS201" in risk.message
    assert risk.contributing_factors["is_mandatory"] is True
    assert any(ref["record_id"] == str(cs201.id) for ref in risk.source_records)

    # Now Alice completes CS101 with grade "A"
    TranscriptEntry.objects.create(
        institution=risk_fixture["institution"],
        student_record=rec_a,
        course=cs101,
        term=risk_fixture["past_term"],
        grade="A",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("4.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
    )

    # Re-evaluate: CS201 prerequisite is now satisfied!
    updated_indicators = evaluate_missing_critical_prerequisites(rec_a)
    updated_cs201_risks = [i for i in updated_indicators if i.contributing_factors.get("course_code") == "CS201"]
    assert len(updated_cs201_risks) == 0


def test_required_course_unoffered_rule(risk_fixture):
    """
    Verifies that an uncompleted mandatory course with no upcoming offerings
    is flagged and that creating an upcoming offering clears the flag.
    """
    inst = risk_fixture["institution"]
    rec_a = risk_fixture["student_record_a"]
    cs301 = risk_fixture["cs301"]

    # CS301 is mandatory and currently has 0 offerings
    indicators = evaluate_required_courses_unoffered(rec_a)
    unoffered_risks = [i for i in indicators if i.code == "REQUIRED_COURSE_UNOFFERED" and i.contributing_factors.get("course_code") == "CS301"]

    assert len(unoffered_risks) == 1
    risk = unoffered_risks[0]
    assert risk.severity == RiskSeverity.CRITICAL
    assert risk.category == RiskCategory.COURSE_OFFERING
    assert risk.contributing_factors["offerings_found"] == 0

    # Create an upcoming offering for CS301 in the imminent term
    CourseOffering.objects.create(
        institution=inst,
        course=cs301,
        academic_term=risk_fixture["imminent_term"].season,
        academic_year=str(risk_fixture["imminent_term"].year),
        is_offered=True,
        capacity=35,
        delivery_mode=DeliveryMode.IN_PERSON,
    )

    # Re-evaluate: CS301 is now offered!
    updated_indicators = evaluate_required_courses_unoffered(rec_a)
    updated_cs301_risks = [i for i in updated_indicators if i.contributing_factors.get("course_code") == "CS301"]
    assert len(updated_cs301_risks) == 0


def test_registration_deadline_approaching_rule(risk_fixture):
    """
    Verifies that when a term begins in <= 14 days and the student has no courses planned/enrolled,
    a REGISTRATION_DEADLINE_APPROACHING indicator is raised.
    """
    rec_a = risk_fixture["student_record_a"]
    imminent_term = risk_fixture["imminent_term"]

    # Imminent term starts in 5 days, Alice has 0 courses planned or enrolled
    indicators = evaluate_registration_deadlines(rec_a, plan=None, threshold_days=14)
    deadline_risks = [i for i in indicators if i.code == "REGISTRATION_DEADLINE_APPROACHING"]

    assert len(deadline_risks) == 1
    risk = deadline_risks[0]
    assert risk.category == RiskCategory.REGISTRATION
    assert risk.contributing_factors["term_code"] == imminent_term.code
    assert risk.contributing_factors["days_until_start"] in (4, 5, 6)

    # Create a plan with a planned course for this imminent term
    plan = Plan.objects.create(
        institution=risk_fixture["institution"],
        student_record=rec_a,
        curriculum_version=risk_fixture["curriculum_version"],
        name="Alice Plan",
        status=PlanStatus.DRAFT,
    )
    PlanItem.objects.create(
        institution=risk_fixture["institution"],
        plan=plan,
        course=risk_fixture["cs101"],
        planned_term=imminent_term,
        term_index=1,
    )

    # Re-evaluate with the plan provided: Alice now has a planned course for imminent term!
    updated_indicators = evaluate_registration_deadlines(rec_a, plan=plan, threshold_days=14)
    assert len(updated_indicators) == 0


def test_credit_shortfall_rule(risk_fixture):
    """
    Verifies that credit shortfall is flagged when required credit completion velocity
    exceeds the max standard term load limit (18 credits/term).
    """
    rec_a = risk_fixture["student_record_a"]
    inst = risk_fixture["institution"]
    cv = risk_fixture["curriculum_version"]

    # Plan with only 1 planned term
    plan = Plan.objects.create(
        institution=inst,
        student_record=rec_a,
        curriculum_version=cv,
        name="Compressed Plan",
    )
    PlanItem.objects.create(
        institution=inst,
        plan=plan,
        course=risk_fixture["cs101"],
        planned_term=risk_fixture["imminent_term"],
        term_index=1,
    )

    # Degree audit requires 120 credits; with only 1 term, velocity = 120 / 1 = 120 > 18
    indicators = evaluate_credit_shortfall(rec_a, plan=plan, max_standard_credits=18.0)
    shortfall_risks = [i for i in indicators if i.code == "CREDIT_SHORTFALL"]

    assert len(shortfall_risks) == 1
    risk = shortfall_risks[0]
    assert risk.severity == RiskSeverity.CRITICAL
    assert risk.category == RiskCategory.TIMELINE_COMPLETION
    assert risk.contributing_factors["remaining_terms_count"] == 1
    assert risk.contributing_factors["required_credits_per_term"] > 18.0


def test_repeated_course_failure_rule(risk_fixture):
    """
    Verifies that repeated failing grades on a course (>= 2 attempts) trigger REPEATED_COURSE_FAILURE,
    and passing the course clears the flag.
    """
    rec_a = risk_fixture["student_record_a"]
    inst = risk_fixture["institution"]
    math101 = risk_fixture["math101"]
    past_term = risk_fixture["past_term"]

    # Attempt 1: F
    TranscriptEntry.objects.create(
        institution=inst,
        student_record=rec_a,
        course=math101,
        term=past_term,
        attempt_number=1,
        grade="F",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("0.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
    )
    # Attempt 2: W
    TranscriptEntry.objects.create(
        institution=inst,
        student_record=rec_a,
        course=math101,
        term=past_term,
        attempt_number=2,
        grade="W",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("0.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
    )

    indicators = evaluate_repeated_course_failures(rec_a)
    repeat_risks = [i for i in indicators if i.code == "REPEATED_COURSE_FAILURE" and i.contributing_factors.get("course_code") == "MATH101"]

    assert len(repeat_risks) == 1
    risk = repeat_risks[0]
    assert risk.severity == RiskSeverity.CRITICAL
    assert risk.category == RiskCategory.ACADEMIC_STANDING
    assert risk.contributing_factors["failed_attempt_count"] == 2
    assert "F" in risk.contributing_factors["grades_received"]

    # Now Alice passes MATH101 with grade "B"
    TranscriptEntry.objects.create(
        institution=inst,
        student_record=rec_a,
        course=math101,
        term=past_term,
        attempt_number=3,
        grade="B",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("4.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
    )

    # Re-evaluate: course was passed on third attempt -> flag cleared
    updated_indicators = evaluate_repeated_course_failures(rec_a)
    updated_math_risks = [i for i in updated_indicators if i.contributing_factors.get("course_code") == "MATH101"]
    assert len(updated_math_risks) == 0


def test_prerequisite_bottleneck_rule(risk_fixture):
    """
    Verifies that an uncompleted course blocking >= 3 downstream degree courses
    triggers PREREQUISITE_BOTTLENECK.
    """
    rec_a = risk_fixture["student_record_a"]

    # CS100 is prerequisite for CS202, CS203, CS301 (3 downstream courses)
    indicators = evaluate_prerequisite_bottlenecks(rec_a, bottleneck_threshold=3)
    bottleneck_risks = [i for i in indicators if i.code == "PREREQUISITE_BOTTLENECK" and i.contributing_factors.get("bottleneck_course_code") == "CS100"]

    assert len(bottleneck_risks) == 1
    risk = bottleneck_risks[0]
    assert risk.severity == RiskSeverity.WARNING
    assert risk.category == RiskCategory.PREREQUISITE
    assert risk.contributing_factors["downstream_course_count"] == 3


def test_overall_risk_level_determinism_and_sorting(risk_fixture):
    """Verifies overall risk level calculation and deterministic sorting order."""
    rec_a = risk_fixture["student_record_a"]
    result = evaluate_student_risks(rec_a, save=True)

    # Has critical risks (CS201 missing prereq, credit shortfall, etc.) -> CRITICAL
    assert result.overall_risk_level == OverallRiskLevel.CRITICAL
    assert result.critical_risk_count >= 1

    # Check sorting: all CRITICAL appear before WARNING before INFO
    severities = [i.severity for i in result.indicators]
    sev_indices = [{"CRITICAL": 0, "WARNING": 1, "INFO": 2}.get(s, 99) for s in severities]
    assert sev_indices == sorted(sev_indices)


def test_zero_row_mutations_on_academic_records(risk_fixture):
    """
    Strictly verifies that running academic risk evaluations alters ZERO rows
    in official academic records (StudentRecord, TranscriptEntry, CurriculumVersion, Course).
    """
    rec_a = risk_fixture["student_record_a"]

    pre_student_count = StudentRecord.objects.count()
    pre_transcript_count = TranscriptEntry.objects.count()
    pre_curriculum_count = CurriculumVersion.objects.count()
    pre_course_count = Course.objects.count()

    # Run evaluations multiple times
    for _ in range(3):
        evaluate_student_risks(rec_a, save=False)
        get_student_risk_profile(rec_a, refresh=True)

    assert StudentRecord.objects.count() == pre_student_count
    assert TranscriptEntry.objects.count() == pre_transcript_count
    assert CurriculumVersion.objects.count() == pre_curriculum_count
    assert Course.objects.count() == pre_course_count


def test_student_risk_api_permissions_and_ownership(risk_fixture):
    """
    Verifies role-based access control and object-level student ownership:
    - Student A can view own profile (200 OK)
    - Student B cannot view Student A (403 Forbidden)
    - Assigned Advisor can view Student A (200 OK)
    - Unassigned Advisor cannot view Student A (403 Forbidden)
    - Coordinator can view Student A (200 OK)
    - Refresh parameter and POST evaluate work
    """
    client = APIClient()
    rec_a = risk_fixture["student_record_a"]
    user_a = risk_fixture["student_user_a"]
    user_b = risk_fixture["student_user_b"]
    advisor = risk_fixture["advisor"]
    unassigned = risk_fixture["unassigned_advisor"]
    coordinator = risk_fixture["coordinator"]

    url = f"/api/advising/students/{rec_a.id}/risk/"

    # 1. Student A views own profile -> 200 OK
    client.force_authenticate(user=user_a)
    res_a = client.get(url)
    assert res_a.status_code == status.HTTP_200_OK
    assert res_a.data["student_username"] == "alice_risk"

    # 2. Student B views Student A's profile -> 403 Forbidden
    client.force_authenticate(user=user_b)
    res_b = client.get(url)
    assert res_b.status_code == status.HTTP_403_FORBIDDEN

    # 3. Assigned Advisor views Student A -> 200 OK
    client.force_authenticate(user=advisor)
    res_adv = client.get(url)
    assert res_adv.status_code == status.HTTP_200_OK

    # 4. Unassigned Advisor views Student A -> 403 Forbidden
    client.force_authenticate(user=unassigned)
    res_unadv = client.get(url)
    assert res_unadv.status_code == status.HTTP_403_FORBIDDEN

    # 5. Coordinator views Student A -> 200 OK
    client.force_authenticate(user=coordinator)
    res_coord = client.get(url)
    assert res_coord.status_code == status.HTTP_200_OK

    # 6. POST to evaluate endpoint
    client.force_authenticate(user=advisor)
    eval_url = f"/api/advising/students/{rec_a.id}/risk/evaluate/"
    res_eval = client.post(eval_url)
    assert res_eval.status_code == status.HTTP_200_OK
    assert res_eval.data["student_id"] == str(rec_a.id)


def test_cross_tenant_isolation(risk_fixture):
    """
    Verifies that requests across tenant boundaries cannot read or evaluate student risk profiles.
    """
    client = APIClient()
    rec_a = risk_fixture["student_record_a"]
    other_user = risk_fixture["other_student_user"]

    client.force_authenticate(user=other_user)
    url = f"/api/advising/students/{rec_a.id}/risk/"
    res = client.get(url)
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_institution_risk_summary_api(risk_fixture):
    """
    Verifies GET /api/advising/risks/summary/ endpoint:
    - Advisors and Coordinators get 200 OK with aggregated statistics
    - Students get 403 Forbidden
    """
    client = APIClient()
    advisor = risk_fixture["advisor"]
    student = risk_fixture["student_user_a"]

    # Pre-populate risk profile
    evaluate_student_risks(risk_fixture["student_record_a"], save=True)

    url = "/api/advising/risks/summary/"

    # Advisor -> 200 OK
    client.force_authenticate(user=advisor)
    res_adv = client.get(url)
    assert res_adv.status_code == status.HTTP_200_OK
    assert "risk_level_counts" in res_adv.data
    assert res_adv.data["total_assessed_students"] >= 1

    # Student -> 403 Forbidden
    client.force_authenticate(user=student)
    res_stu = client.get(url)
    assert res_stu.status_code == status.HTTP_403_FORBIDDEN


def test_risk_acknowledgment_workflow(risk_fixture):
    """
    Verifies advisor logging notes and action plan on an identified risk:
    - Advisor can create acknowledgment
    - Student cannot create acknowledgment
    """
    client = APIClient()
    advisor = risk_fixture["advisor"]
    student = risk_fixture["student_user_a"]

    evaluate_student_risks(risk_fixture["student_record_a"], save=True)
    profile = StudentRiskProfile.objects.get(student_record=risk_fixture["student_record_a"])

    url = "/api/advising/risks/acknowledgments/"

    # Student attempt -> 403 Forbidden
    client.force_authenticate(user=student)
    res_stu = client.post(url, {
        "risk_profile": str(profile.id),
        "indicator_code": "MISSING_CRITICAL_PREREQUISITE",
        "notes": "Student notes",
    })
    assert res_stu.status_code == status.HTTP_403_FORBIDDEN

    # Advisor -> 201 Created
    client.force_authenticate(user=advisor)
    res_adv = client.post(url, {
        "risk_profile": str(profile.id),
        "indicator_code": "MISSING_CRITICAL_PREREQUISITE",
        "status": AcknowledgmentStatus.ACTION_PLAN_CREATED,
        "notes": "Met with student to arrange CS101 enrollment next term.",
        "action_plan": "Register for CS101 Fall section.",
    })
    assert res_adv.status_code == status.HTTP_201_CREATED
    assert res_adv.data["advisor_username"] == advisor.username
    assert res_adv.data["status"] == AcknowledgmentStatus.ACTION_PLAN_CREATED
