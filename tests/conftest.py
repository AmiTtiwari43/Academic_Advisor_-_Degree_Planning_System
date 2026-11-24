import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

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


@pytest.fixture(autouse=True)
def clean_ai_test_environment(monkeypatch):
    """
    By default in unit tests, prevents external live network calls to Gemini or Groq
    unless explicitly patched by a fallback test.
    """
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("SECONDARY_AI_API_KEY", raising=False)


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

    m_student = InstitutionMembership.objects.create(
        user=student_u,
        institution=inst,
        role=Role.STUDENT,
        is_active=True,
    )
    m_advisor = InstitutionMembership.objects.create(
        user=advisor_u,
        institution=inst,
        role=Role.ADVISOR,
        is_active=True,
    )

    UserProfile.objects.create(
        user=student_u,
        preferred_name="Alex",
    )
    UserProfile.objects.create(
        user=advisor_u,
        preferred_name="Dr. Chen",
    )

    # Advisor Assignment
    AdvisorAssignment.objects.create(
        institution=inst,
        advisor=m_advisor,
        student=m_student,
        is_active=True,
    )

    # Student Record on 10-Point GPA Scale
    rec = StudentRecord.objects.create(
        institution=inst,
        student=student_u,
        programme=prog,
        pinned_curriculum=curr_v1,
        enrollment_term=term_f24,
        status=StudentRecordStatus.ACTIVE,
        cached_cgpa=Decimal("8.50"),  # 8.50 / 10.00 Scale
        cached_total_credits=Decimal("8.00"),
    )

    # Transcript Entries on 10-point scale: Alex completed CS-101 (Grade A = 9.0) and MATH-151 (Grade B = 7.0)
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
    TranscriptEntry.objects.create(
        institution=inst,
        student_record=rec,
        course=math151,
        term=term_f24,
        grade="B",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("4.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
        attempt_number=1,
    )

    # In-progress course: CS-201 in FA2024
    TranscriptEntry.objects.create(
        institution=inst,
        student_record=rec,
        course=cs201,
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
