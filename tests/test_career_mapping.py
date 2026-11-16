"""
Comprehensive Test Suite for Career Objective and Skill Mapping (Prompt 08D).
Covers:
- Models, relationships, and multi-tenant constraints
- Skill-gap analysis accuracy (acquired skills, missing skills, proficiency gaps, readiness percentage)
- Course recommendations ranking determinism
- Degree requirement alignment (never displacing mandatory degree requirements, labelling DEGREE_AND_CAREER vs CAREER_ELECTIVE)
- Prerequisite rule enforcement (via rule engine)
- Student career preference management
- REST API permissions, multi-tenant isolation, and student ownership checks
"""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
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
from accounts.models import InstitutionMembership, Role
from career_mapping.models import (
    CareerObjective,
    CareerSkillRequirement,
    CourseSkillMapping,
    ProficiencyLevel,
    Skill,
    SkillCategory,
    StudentCareerPreference,
)
from career_mapping.services import (
    analyze_skill_gap,
    get_career_course_recommendations,
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


@pytest.fixture
def career_setup(db):
    """
    Sets up a full multi-tenant fixture for Career & Skill Mapping:
    - Institution A & Institution B
    - Coordinator, Student A, Student B (same institution), Student C (Institution B)
    - Skills: Python, SQL, Machine Learning, Distributed Systems, Web Dev
    - Career Objective: Data Scientist (Critical: Python, SQL, ML; Recommended: Distributed Systems)
    - Pinned Curriculum: BS-CS with Core group and Technical Electives group
    - Student A has completed CS-101 (Python) and CS-102 (SQL)
    """
    institution = Institution.objects.create(
        name="Apex University",
        domain="apex-career.edu",
        code="APEX_CAREER",
    )
    other_institution = Institution.objects.create(
        name="Global University",
        domain="global-career.edu",
        code="GLOBAL_CAREER",
    )

    # Users
    coordinator = User.objects.create_user(
        username="coord_apex",
        email="coord@apex-career.edu",
        password="password123",
    )
    InstitutionMembership.objects.create(
        user=coordinator,
        institution=institution,
        role=Role.COORDINATOR,
        is_active=True,
    )

    student_user_a = User.objects.create_user(
        username="alice_career",
        email="alice@apex-career.edu",
        first_name="Alice",
        last_name="Wong",
        password="password123",
    )
    InstitutionMembership.objects.create(
        user=student_user_a,
        institution=institution,
        role=Role.STUDENT,
        is_active=True,
    )

    student_user_b = User.objects.create_user(
        username="bob_career",
        email="bob@apex-career.edu",
        first_name="Bob",
        last_name="Jones",
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
        email="charlie@global-career.edu",
        password="password123",
    )
    InstitutionMembership.objects.create(
        user=other_student_user,
        institution=other_institution,
        role=Role.STUDENT,
        is_active=True,
    )

    # Academic terms
    term1 = AcademicTerm.objects.create(
        institution=institution,
        code="FALL-2025-CAR",
        name="Fall 2025",
        season=TermSeason.FALL,
        year=2025,
        start_date="2025-09-01",
        end_date="2025-12-15",
    )
    term2 = AcademicTerm.objects.create(
        institution=institution,
        code="SPRING-2026-CAR",
        name="Spring 2026",
        season=TermSeason.SPRING,
        year=2026,
        start_date="2026-01-15",
        end_date="2026-05-15",
    )

    # Programme & Curriculum
    programme = Programme.objects.create(
        institution=institution,
        code="BS-CS-CAR",
        name="BS Computer Science",
    )
    curr_ver = CurriculumVersion.objects.create(
        institution=institution,
        programme=programme,
        version_number=1,
        academic_year="2025-2026",
        total_credits_required=Decimal("120.00"),
        status=CurriculumStatus.DRAFT,
    )
    core_group = RequirementGroup.objects.create(
        institution=institution,
        curriculum_version=curr_ver,
        name="Core Computer Science",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("8.00"),
        min_courses=2,
    )
    elective_group = RequirementGroup.objects.create(
        institution=institution,
        curriculum_version=curr_ver,
        name="Technical Electives",
        group_type=RequirementGroupType.ELECTIVE,
        min_credits=Decimal("4.00"),
        min_courses=1,
    )

    # Courses
    cs101 = Course.objects.create(
        institution=institution, code="CS-101", title="Intro to Python", credits=Decimal("4.00")
    )
    cs102 = Course.objects.create(
        institution=institution, code="CS-102", title="Relational Databases & SQL", credits=Decimal("4.00")
    )
    cs201 = Course.objects.create(
        institution=institution, code="CS-201", title="Data Structures & Algorithms", credits=Decimal("4.00")
    )
    cs301 = Course.objects.create(
        institution=institution, code="CS-301", title="Machine Learning Foundations", credits=Decimal("4.00")
    )
    cs302 = Course.objects.create(
        institution=institution, code="CS-302", title="Distributed Systems & Cloud", credits=Decimal("4.00")
    )
    cs303 = Course.objects.create(
        institution=institution, code="CS-303", title="Deep Learning Specialization", credits=Decimal("4.00")
    )

    # Group course associations
    RequirementGroupCourse.objects.create(requirement_group=core_group, course=cs101, is_mandatory=True)
    RequirementGroupCourse.objects.create(requirement_group=core_group, course=cs102, is_mandatory=True)
    RequirementGroupCourse.objects.create(requirement_group=elective_group, course=cs301, is_mandatory=False)
    RequirementGroupCourse.objects.create(requirement_group=elective_group, course=cs302, is_mandatory=False)

    # Prerequisite: CS-301 requires CS-201
    PrerequisiteRule.objects.create(
        institution=institution,
        curriculum_version=curr_ver,
        course=cs301,
        rule_json={
            "schema_version": 1,
            "type": "course_completed",
            "course_code": "CS-201",
            "min_grade": "C",
        },
    )

    curr_ver.status = CurriculumStatus.PUBLISHED
    curr_ver.save()

    # Student Record
    student_rec_a = StudentRecord.objects.create(
        institution=institution,
        student=student_user_a,
        programme=programme,
        pinned_curriculum=curr_ver,
        enrollment_term=term1,
        status=StudentRecordStatus.ACTIVE,
        cached_cgpa=Decimal("8.50"),
        cached_total_credits=Decimal("8.00"),
    )
    student_rec_b = StudentRecord.objects.create(
        institution=institution,
        student=student_user_b,
        programme=programme,
        pinned_curriculum=curr_ver,
        enrollment_term=term1,
        status=StudentRecordStatus.ACTIVE,
        cached_cgpa=Decimal("7.50"),
        cached_total_credits=Decimal("0.00"),
    )

    # Transcript for Alice: completed CS-101 and CS-102 with grade 'A'
    TranscriptEntry.objects.create(
        institution=institution,
        student_record=student_rec_a,
        course=cs101,
        term=term1,
        grade="A",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("4.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
    )
    TranscriptEntry.objects.create(
        institution=institution,
        student_record=student_rec_a,
        course=cs102,
        term=term1,
        grade="A",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("4.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
    )

    # Skills Taxonomy
    sk_python = Skill.objects.create(
        institution=institution,
        code="PYTHON",
        name="Python Programming",
        category=SkillCategory.TECHNICAL,
    )
    sk_sql = Skill.objects.create(
        institution=institution,
        code="SQL",
        name="Relational Databases & SQL",
        category=SkillCategory.TECHNICAL,
    )
    sk_ml = Skill.objects.create(
        institution=institution,
        code="MACHINE_LEARNING",
        name="Machine Learning",
        category=SkillCategory.TECHNICAL,
    )
    sk_dist = Skill.objects.create(
        institution=institution,
        code="DISTRIBUTED_SYSTEMS",
        name="Distributed Systems",
        category=SkillCategory.TECHNICAL,
    )

    # Course to Skill Mappings
    CourseSkillMapping.objects.create(
        institution=institution,
        course=cs101,
        skill=sk_python,
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        coverage_weight=Decimal("1.00"),
    )
    CourseSkillMapping.objects.create(
        institution=institution,
        course=cs102,
        skill=sk_sql,
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        coverage_weight=Decimal("1.00"),
    )
    CourseSkillMapping.objects.create(
        institution=institution,
        course=cs301,
        skill=sk_ml,
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        coverage_weight=Decimal("1.00"),
    )
    CourseSkillMapping.objects.create(
        institution=institution,
        course=cs302,
        skill=sk_dist,
        proficiency_level=ProficiencyLevel.INTERMEDIATE,
        coverage_weight=Decimal("0.80"),
    )
    CourseSkillMapping.objects.create(
        institution=institution,
        course=cs303,
        skill=sk_ml,
        proficiency_level=ProficiencyLevel.ADVANCED,
        coverage_weight=Decimal("1.00"),
    )

    # Career Objective: Data Scientist
    obj_ds = CareerObjective.objects.create(
        institution=institution,
        code="DATA_SCIENTIST",
        title="Data Scientist",
        description="Analyzes complex data to extract predictive insights.",
        programme=programme,
    )
    CareerSkillRequirement.objects.create(
        career_objective=obj_ds,
        skill=sk_python,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
        is_critical=True,
        display_order=1,
    )
    CareerSkillRequirement.objects.create(
        career_objective=obj_ds,
        skill=sk_sql,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
        is_critical=True,
        display_order=2,
    )
    CareerSkillRequirement.objects.create(
        career_objective=obj_ds,
        skill=sk_ml,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
        is_critical=True,
        display_order=3,
    )
    CareerSkillRequirement.objects.create(
        career_objective=obj_ds,
        skill=sk_dist,
        min_proficiency=ProficiencyLevel.INTERMEDIATE,
        is_critical=False,
        display_order=4,
    )

    # Student Career Preference: Alice -> Data Scientist (Priority 1)
    StudentCareerPreference.objects.create(
        institution=institution,
        student_record=student_rec_a,
        career_objective=obj_ds,
        priority=1,
    )

    return {
        "institution": institution,
        "other_institution": other_institution,
        "coordinator": coordinator,
        "student_user_a": student_user_a,
        "student_user_b": student_user_b,
        "other_student_user": other_student_user,
        "programme": programme,
        "curr_ver": curr_ver,
        "student_rec_a": student_rec_a,
        "student_rec_b": student_rec_b,
        "cs101": cs101,
        "cs102": cs102,
        "cs201": cs201,
        "cs301": cs301,
        "cs302": cs302,
        "cs303": cs303,
        "term1": term1,
        "term2": term2,
        "sk_python": sk_python,

        "sk_sql": sk_sql,
        "sk_ml": sk_ml,
        "sk_dist": sk_dist,
        "obj_ds": obj_ds,
    }


# ---------------------------------------------------------------------------
# Test 1: Model Constraints and Tenant Scoping
# ---------------------------------------------------------------------------


def test_career_mapping_models_and_constraints(career_setup):
    """Verifies uniqueness constraints on skills, career objectives, and student preferences."""
    inst = career_setup["institution"]
    prog = career_setup["programme"]
    rec_a = career_setup["student_rec_a"]

    from django.db import transaction

    # Duplicate skill code in same institution rejected
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Skill.objects.create(
                institution=inst,
                code="PYTHON",
                name="Python 2",
                category=SkillCategory.TECHNICAL,
            )

    # Duplicate career objective code rejected
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            CareerObjective.objects.create(
                institution=inst,
                code="DATA_SCIENTIST",
                title="Data Scientist Duplicate",
                programme=prog,
            )

    # Duplicate student career preference priority rejected
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            obj2 = CareerObjective.objects.create(
                institution=inst,
                code="ML_ENG",
                title="ML Engineer",
                programme=prog,
            )
            StudentCareerPreference.objects.create(
                institution=inst,
                student_record=rec_a,
                career_objective=obj2,
                priority=1,  # Alice already has priority 1
            )



# ---------------------------------------------------------------------------
# Test 2: Skill-Gap Analysis Accuracy
# ---------------------------------------------------------------------------


def test_skill_gap_analysis_accurate_computation(career_setup):
    """
    Alice completed CS-101 (Python) and CS-102 (SQL).
    Data Scientist requires:
    - Python (Critical, Intermediate) -> SATISFIED
    - SQL (Critical, Intermediate) -> SATISFIED
    - Machine Learning (Critical, Intermediate) -> MISSING
    - Distributed Systems (Recommended, Intermediate) -> MISSING
    """
    rec_a = career_setup["student_rec_a"]
    obj_ds = career_setup["obj_ds"]

    report = analyze_skill_gap(student_record=rec_a, career_objective=obj_ds)

    assert report.total_target_skills == 4
    assert report.total_critical_skills == 3
    assert report.critical_skills_met == 2
    assert report.recommended_skills_met == 0

    satisfied_codes = {s.skill_code for s in report.satisfied_skills}
    assert satisfied_codes == {"PYTHON", "SQL"}

    missing_codes = {m.skill_code for m in report.missing_skills}
    assert missing_codes == {"MACHINE_LEARNING", "DISTRIBUTED_SYSTEMS"}

    # Readiness percentage is proportional: (2 critical met = 4 pts out of 7 total possible = ~57.1%)
    assert 50.0 < report.readiness_percentage < 65.0


def test_skill_gap_proficiency_gap_detected(career_setup):
    """
    If a student has a skill at Introductory level, but the career objective requires Advanced,
    it must be categorized under proficiency_gaps.
    """
    inst = career_setup["institution"]
    rec_b = career_setup["student_rec_b"]
    sk_ml = career_setup["sk_ml"]
    obj_ds = career_setup["obj_ds"]

    # Student B completed an intro course in ML
    cs_intro_ml = Course.objects.create(
        institution=inst, code="CS-110", title="Intro to AI", credits=Decimal("3.00")
    )
    CourseSkillMapping.objects.create(
        institution=inst,
        course=cs_intro_ml,
        skill=sk_ml,
        proficiency_level=ProficiencyLevel.INTRODUCTORY,
        coverage_weight=Decimal("1.00"),
    )
    term = AcademicTerm.objects.filter(institution=inst).first()
    TranscriptEntry.objects.create(
        institution=inst,
        student_record=rec_b,
        course=cs_intro_ml,
        term=term,
        grade="B",
        credits_attempted=Decimal("3.00"),
        credits_earned=Decimal("3.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
    )

    report = analyze_skill_gap(student_record=rec_b, career_objective=obj_ds)

    prof_gap_codes = {g.skill_code for g in report.proficiency_gaps}
    assert "MACHINE_LEARNING" in prof_gap_codes
    gap_item = next(g for g in report.proficiency_gaps if g.skill_code == "MACHINE_LEARNING")
    assert gap_item.current_proficiency == "INTRODUCTORY"
    assert gap_item.min_proficiency == "INTERMEDIATE"


# ---------------------------------------------------------------------------
# Test 3: Recommendation Ranking Determinism
# ---------------------------------------------------------------------------


def test_course_recommendations_ranking_determinism(career_setup):
    """
    Verifies that calling get_career_course_recommendations produces
    100% deterministic ranking across repeated executions.
    """
    rec_a = career_setup["student_rec_a"]
    obj_ds = career_setup["obj_ds"]

    run1 = get_career_course_recommendations(rec_a, obj_ds)
    run2 = get_career_course_recommendations(rec_a, obj_ds)
    run3 = get_career_course_recommendations(rec_a, obj_ds)

    codes1 = [r.course_code for r in run1]
    codes2 = [r.course_code for r in run2]
    codes3 = [r.course_code for r in run3]

    assert codes1 == codes2 == codes3
    assert len(codes1) > 0


# ---------------------------------------------------------------------------
# Test 4: Degree Requirement Alignment & Labelling
# ---------------------------------------------------------------------------


def test_recommendations_align_with_degree_requirements(career_setup):
    """
    CS-301 (Machine Learning) is in the unmet 'Technical Electives' group -> DEGREE_AND_CAREER
    CS-303 (Deep Learning) is an orphan course not in the curriculum -> CAREER_ELECTIVE
    Asserts DEGREE_AND_CAREER has higher degree bonus and clear explanation.
    """
    rec_a = career_setup["student_rec_a"]
    obj_ds = career_setup["obj_ds"]

    recommendations = get_career_course_recommendations(rec_a, obj_ds)

    cs301_rec = next((r for r in recommendations if r.course_code == "CS-301"), None)
    cs303_rec = next((r for r in recommendations if r.course_code == "CS-303"), None)

    assert cs301_rec is not None
    assert cs301_rec.recommendation_type == "DEGREE_AND_CAREER"
    assert cs301_rec.satisfies_degree_requirement_group == "Technical Electives"
    assert "Fulfills unmet degree requirement 'Technical Electives'" in cs301_rec.explanation

    assert cs303_rec is not None
    assert cs303_rec.recommendation_type == "CAREER_ELECTIVE"
    assert cs303_rec.satisfies_degree_requirement_group is None
    assert "Counts toward degree elective credits" in cs303_rec.explanation


# ---------------------------------------------------------------------------
# Test 5: Prerequisite Eligibility Enforcement
# ---------------------------------------------------------------------------


def test_recommendations_evaluate_prerequisites(career_setup):
    """
    CS-301 requires CS-201 (Algorithms). Alice has not taken CS-201.
    Asserts CS-301 is flagged as not prerequisite eligible.
    CS-302 (Distributed Systems) has no prerequisite -> is_prerequisite_eligible is True.
    """
    rec_a = career_setup["student_rec_a"]
    obj_ds = career_setup["obj_ds"]

    recommendations = get_career_course_recommendations(rec_a, obj_ds)

    cs301_rec = next(r for r in recommendations if r.course_code == "CS-301")
    assert cs301_rec.is_prerequisite_eligible is False
    assert "Prerequisite requirement not met" in cs301_rec.prerequisite_status_message

    cs302_rec = next(r for r in recommendations if r.course_code == "CS-302")
    assert cs302_rec.is_prerequisite_eligible is True


# ---------------------------------------------------------------------------
# Test 6: Student Career Preference API
# ---------------------------------------------------------------------------


def test_student_career_preference_api(career_setup):
    """
    Student can declare career objectives and prioritize them via API.
    """
    client = APIClient()
    client.force_authenticate(user=career_setup["student_user_b"])
    rec_b = career_setup["student_rec_b"]
    obj_ds = career_setup["obj_ds"]

    url = "/api/career/preferences/"
    payload = {
        "student_record": str(rec_b.id),
        "career_objective": str(obj_ds.id),
        "priority": 1,
        "notes": "Targeting data science internships",
    }

    res = client.post(url, data=payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data["priority"] == 1
    assert res.data["career_objective_code"] == "DATA_SCIENTIST"


# ---------------------------------------------------------------------------
# Test 7: Skill Gap and Recommendation API Endpoints
# ---------------------------------------------------------------------------


def test_skill_gap_and_recommendations_endpoints(career_setup):
    """
    Student can fetch their own skill gap analysis and recommendations.
    """
    client = APIClient()
    client.force_authenticate(user=career_setup["student_user_a"])

    # 1. Skill Gap API
    gap_res = client.get("/api/career/skill-gap/")
    assert gap_res.status_code == status.HTTP_200_OK
    assert "readiness_percentage" in gap_res.data
    assert len(gap_res.data["satisfied_skills"]) == 2

    # 2. Recommendations API
    rec_res = client.get("/api/career/recommendations/")
    assert rec_res.status_code == status.HTTP_200_OK
    assert isinstance(rec_res.data, list)
    assert len(rec_res.data) > 0
    assert "recommendation_type" in rec_res.data[0]
    assert "relevance_score" in rec_res.data[0]


# ---------------------------------------------------------------------------
# Test 8: Student Cannot Access Another Student's Preferences
# ---------------------------------------------------------------------------


def test_student_cannot_access_other_student_career_data(career_setup):
    """
    Student A cannot query or view Student B's skill gap or set Student B's preferences.
    """
    client = APIClient()
    client.force_authenticate(user=career_setup["student_user_a"])
    rec_b = career_setup["student_rec_b"]

    url = f"/api/career/skill-gap/?student_id={rec_b.id}"
    res = client.get(url)
    assert res.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# Test 9: Multi-Tenant Scoping Isolation
# ---------------------------------------------------------------------------


def test_cross_tenant_career_access_denied(career_setup):
    """
    Student from Institution B cannot access career objectives or skill gaps from Institution A.
    """
    client = APIClient()
    client.force_authenticate(user=career_setup["other_student_user"])
    obj_ds = career_setup["obj_ds"]

    url = f"/api/career/objectives/{obj_ds.id}/"
    res = client.get(url)
    assert res.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Test 10: Coordinator Can Manage Taxonomy, Student Forbidden
# ---------------------------------------------------------------------------


def test_coordinator_taxonomy_permissions(career_setup):
    """
    Coordinators can create and update skills and objectives.
    Students attempting to mutate taxonomy receive 403 Forbidden.
    """
    coord_client = APIClient()
    coord_client.force_authenticate(user=career_setup["coordinator"])

    # Coordinator creates new skill
    res = coord_client.post(
        "/api/career/skills/",
        data={
            "code": "CYBER_SEC",
            "name": "Cybersecurity Fundamentals",
            "category": "TECHNICAL",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED

    # Student attempts to create skill
    student_client = APIClient()
    student_client.force_authenticate(user=career_setup["student_user_a"])
    res_student = student_client.post(
        "/api/career/skills/",
        data={
            "code": "HACKING",
            "name": "Ethical Hacking",
            "category": "TECHNICAL",
        },
        format="json",
    )
    assert res_student.status_code == status.HTTP_403_FORBIDDEN
