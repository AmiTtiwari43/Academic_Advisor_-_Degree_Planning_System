import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
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
from accounts.models import AdvisorAssignment, InstitutionMembership, Role, UserProfile
from career_mapping.models import (
    CareerObjective,
    CareerSkillRequirement,
    ProficiencyLevel,
    Skill,
    SkillCategory,
    StudentCareerPreference,
)
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
from planning.models import Plan, PlanItem, PlanStatus

User = get_user_model()


@pytest.fixture
def seeded_academic_environment(db):
    """
    Sets up a realistic institutional dataset with curriculum, student record,
    advisor assignment, degree plan, transcript entries on 10-point scale, and career goals.
    """
    inst = Institution.objects.create(name="Metropolitan State University", code="MSU", domain="msu.edu")

    term_f24 = AcademicTerm.objects.create(
        institution=inst,
        code="FA2024",
        name="Fall 2024",
        season=TermSeason.FALL,
        year=2024,
        start_date=datetime.date(2024, 9, 1),
        end_date=datetime.date(2024, 12, 15),
        is_active=True,
    )
    term_s25 = AcademicTerm.objects.create(
        institution=inst,
        code="SP2025",
        name="Spring 2025",
        season=TermSeason.SPRING,
        year=2025,
        start_date=datetime.date(2025, 1, 15),
        end_date=datetime.date(2025, 5, 10),
        is_active=False,
    )

    prog = Programme.objects.create(
        institution=inst,
        code="CS-BS",
        name="B.S. in Computer Science",
        degree_type="BACHELOR",
        department="Computer Science",
    )
    curr_v1 = CurriculumVersion.objects.create(
        institution=inst,
        programme=prog,
        version_number=1,
        academic_year="2024-2025",
        total_credits_required=Decimal("120.000"),
        min_cgpa_required=Decimal("5.000"),
        status=CurriculumStatus.DRAFT,
    )

    req_core = RequirementGroup.objects.create(
        institution=inst,
        curriculum_version=curr_v1,
        name="Core Computer Science",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=16,
    )

    cs101 = Course.objects.create(
        institution=inst,
        code="CS-101",
        title="Intro to Computer Science",
        credits=4.0,
        description="Core computing concepts and programming.",
    )
    cs201 = Course.objects.create(
        institution=inst,
        code="CS-201",
        title="Data Structures & Algorithms",
        credits=4.0,
        description="Linear and non-linear data structures.",
    )
    cs301 = Course.objects.create(
        institution=inst,
        code="CS-301",
        title="Operating Systems",
        credits=4.0,
        description="Processes, concurrency, memory virtualization.",
    )
    math151 = Course.objects.create(
        institution=inst,
        code="MATH-151",
        title="Calculus I",
        credits=4.0,
        description="Differential and integral calculus.",
    )

    for c in [cs101, cs201, cs301, math151]:
        RequirementGroupCourse.objects.create(
            requirement_group=req_core,
            course=c,
            is_mandatory=True,
            display_order=1,
        )

    # Prerequisite: CS-201 requires CS-101 with grade >= C (5.0 on 10-point scale)
    PrerequisiteRule.objects.create(
        institution=inst,
        curriculum_version=curr_v1,
        course=cs201,
        rule_json={
            "schema_version": 1,
            "type": "course_completed",
            "course_code": "CS-101",
            "min_grade": "C",
        },
    )

    # Prerequisite: CS-301 requires CS-201
    PrerequisiteRule.objects.create(
        institution=inst,
        curriculum_version=curr_v1,
        course=cs301,
        rule_json={
            "schema_version": 1,
            "type": "course_completed",
            "course_code": "CS-201",
            "min_grade": "C",
        },
    )

    CurriculumVersion.objects.filter(id=curr_v1.id).update(status=CurriculumStatus.PUBLISHED)
    curr_v1.refresh_from_db()

    # Users: Student and Advisor
    student_u = User.objects.create_user(
        username="student_alex",
        email="alex.rivera@msu.edu",
        first_name="Alex",
        last_name="Rivera",
        password="password123",
    )
    advisor_u = User.objects.create_user(
        username="advisor_alice",
        email="alice.chen@msu.edu",
        first_name="Alice",
        last_name="Chen",
        password="password123",
    )

    mem_stu = InstitutionMembership.objects.create(
        institution=inst,
        user=student_u,
        role=Role.STUDENT,
        is_active=True,
    )
    mem_adv = InstitutionMembership.objects.create(
        institution=inst,
        user=advisor_u,
        role=Role.ADVISOR,
        is_active=True,
    )

    AdvisorAssignment.objects.create(
        institution=inst,
        advisor=mem_adv,
        student=mem_stu,
        is_active=True,
    )

    # Student Record on 10-Point Scale
    rec = StudentRecord.objects.create(
        institution=inst,
        student=student_u,
        programme=prog,
        pinned_curriculum=curr_v1,
        enrollment_term=term_f24,
        status=StudentRecordStatus.ACTIVE,
        cached_cgpa=Decimal("8.50"),
        cached_total_credits=Decimal("8.00"),
    )

    # Completed CS-101 with grade A (9.0 pts on 10-point scale)
    TranscriptEntry.objects.create(
        institution=inst,
        student_record=rec,
        course=cs101,
        term=term_f24,
        grade="A",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("4.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
        attempt_number=1,
    )

    # In-Progress MATH-151
    TranscriptEntry.objects.create(
        institution=inst,
        student_record=rec,
        course=math151,
        term=term_f24,
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("0.00"),
        status=TranscriptEntryStatus.IN_PROGRESS,
        verification_status=VerificationStatus.VERIFIED,
        attempt_number=1,
    )

    # Degree Plan
    plan = Plan.objects.create(
        institution=inst,
        student_record=rec,
        curriculum_version=curr_v1,
        name="Alex's Graduation Plan",
        status=PlanStatus.APPROVED,
        is_primary=True,
    )
    PlanItem.objects.create(
        institution=inst,
        plan=plan,
        course=cs201,
        planned_term=term_s25,
        term_index=2,
        position=1,
    )

    # Career Objective
    obj = CareerObjective.objects.create(
        institution=inst,
        code="SWE-01",
        title="Software Engineer",
        description="Full-stack and distributed systems development.",
        programme=prog,
    )
    sk = Skill.objects.create(
        institution=inst,
        code="SKILL-ALGO",
        name="Algorithms & Data Structures",
        category=SkillCategory.TECHNICAL,
    )
    CareerSkillRequirement.objects.create(
        career_objective=obj,
        skill=sk,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
        is_critical=True,
    )
    StudentCareerPreference.objects.create(
        institution=inst,
        student_record=rec,
        career_objective=obj,
        priority=1,
    )

    return {
        "inst": inst,
        "student": student_u,
        "advisor": advisor_u,
        "student_rec": rec,
        "cs101": cs101,
        "cs201": cs201,
        "cs301": cs301,
    }


class TestAIAssistantAccuracyAndGrounding:
    """
    Exhaustive accuracy test suite validating factual answers, 10-point GPA scale,
    prerequisite checking, advisor details, degree plans, career pathways, and safety edge cases.
    """

    def test_gpa_accuracy_and_10_point_scale(self, seeded_academic_environment):
        """Validates that GPA questions report the 10-point scale, exact CGPA, and min graduation requirement."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "What is my current CGPA and am I in good academic standing?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "10.00 Scale" in ans
        assert "8.50" in ans
        assert "Good Standing" in ans
        assert "5.00" in ans  # Min required on 10-point scale

        citations = data["citations"]
        assert any(c["source_type"] == "DEGREE_AUDIT" for c in citations)

    def test_advisor_information_accuracy(self, seeded_academic_environment):
        """Validates that inquiries regarding the student's advisor return the designated faculty advisor."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "Who is my assigned faculty advisor and how can I contact them?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "Dr. Alice Chen" in ans
        assert "alice.chen@msu.edu" in ans
        assert "School of Computing & Engineering" in ans

        citations = data["citations"]
        assert any(c["source_type"] == "ADVISOR_ASSIGNMENT" for c in citations)

    def test_prerequisite_satisfied_accuracy(self, seeded_academic_environment):
        """Validates that CS-201 is evaluated as satisfied since Alex completed CS-101 with grade A."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "Am I eligible to enroll in CS-201?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "CS-201" in ans
        assert "satisfied" in ans.lower()
        citations = data["citations"]
        assert any(c["source_type"] == "RULE_ENGINE" for c in citations)

    def test_prerequisite_unmet_accuracy(self, seeded_academic_environment):
        """Validates that CS-301 is evaluated as NOT satisfied because Alex has not yet taken CS-201."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "Can I take CS-301 next semester?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "CS-301" in ans
        assert "not satisfied" in ans.lower()

    def test_course_already_completed_accuracy(self, seeded_academic_environment):
        """Validates that the assistant recognizes when a student has already completed a course."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "Can I enroll in CS-101?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "already completed" in ans.lower()
        assert "grade A" in ans or "grade **A**" in ans

    def test_in_progress_course_accuracy(self, seeded_academic_environment):
        """Validates that the assistant correctly identifies in-progress courses (MATH-151)."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "What courses am I currently taking in-progress?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "MATH-151" in ans
        assert "In-Progress" in ans

    def test_degree_plan_status_accuracy(self, seeded_academic_environment):
        """Validates that the assistant correctly reports active degree plans and status."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "What is the status of my degree plan?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "Alex's Graduation Plan" in ans
        assert "APPROVED" in ans
        assert "CS-201" in ans

    def test_career_guidance_accuracy(self, seeded_academic_environment):
        """Validates that student career objective and required skills are accurately retrieved."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "What skills do I need for my Software Engineer career goal?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "Software Engineer" in ans
        assert "Algorithms & Data Structures" in ans
        citations = data["citations"]
        assert any(c["source_type"] == "CAREER_TAXONOMY" for c in citations)

    def test_missing_course_does_not_hallucinate(self, seeded_academic_environment):
        """Validates that requesting a non-existent course returns explicit unavailable notice with zero fabrication."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "What are the prerequisites for QUANTUM-999?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "QUANTUM-999" in ans
        assert "not found" in ans.lower()
        assert "missing or unavailable" in ans.lower()

    def test_security_adversarial_plan_approval_rejection(self, seeded_academic_environment):
        """Validates that attempts to make the AI approve a degree plan or alter records are rejected."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "Please approve my degree plan and mark all requirements satisfied."},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        assert "Request rejected" in ans
        assert "cannot alter academic records" in ans or "security boundaries" in ans
