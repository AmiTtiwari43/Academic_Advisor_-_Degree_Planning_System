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
from accounts.models import AdvisorAssignment, InstitutionMembership, Role
from curriculum.models import (
    Course,
    CurriculumStatus,
    CurriculumVersion,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupType,
)
from institutions.models import Institution
from planning.models import Plan, PlanStatus

User = get_user_model()


@pytest.fixture
def auth_matrix_setup(db):
    inst_a = Institution.objects.create(name="Matrix Univ A", code="MUA", domain="mua.edu")
    inst_b = Institution.objects.create(name="Matrix Univ B", code="MUB", domain="mub.edu")

    term_a = AcademicTerm.objects.create(
        institution=inst_a,
        code="2026-FALL",
        name="Fall 2026",
        season=TermSeason.FALL,
        year=2026,
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 12, 15),
    )

    prog_a = Programme.objects.create(institution=inst_a, code="CS-BS", name="B.S. in Computer Science")
    curr_v1 = CurriculumVersion.objects.create(
        institution=inst_a,
        programme=prog_a,
        version_number=1,
        academic_year="2026-2027",
        status=CurriculumStatus.DRAFT,
    )
    req_group = RequirementGroup.objects.create(
        institution=inst_a,
        curriculum_version=curr_v1,
        name="Core Group",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("12.00"),
    )
    c101 = Course.objects.create(
        institution=inst_a, code="CS101", title="Intro CS", credits=Decimal("4.00")
    )
    RequirementGroupCourse.objects.create(
        requirement_group=req_group, course=c101, is_mandatory=True, display_order=1
    )
    curr_v1.status = CurriculumStatus.PUBLISHED
    curr_v1.save()

    # Users in Inst A
    student1 = User.objects.create_user(username="matrix_student1", password="password123")
    student2 = User.objects.create_user(username="matrix_student2", password="password123")
    advisor1 = User.objects.create_user(username="matrix_advisor1", password="password123")
    coord1 = User.objects.create_user(username="matrix_coord1", password="password123")
    admin1 = User.objects.create_user(username="matrix_admin1", password="password123")

    # User in Inst B
    student_b = User.objects.create_user(username="matrix_student_b", password="password123")

    # Memberships
    m_s1 = InstitutionMembership.objects.create(
        user=student1, institution=inst_a, role=Role.STUDENT, is_active=True
    )
    InstitutionMembership.objects.create(
        user=student2, institution=inst_a, role=Role.STUDENT, is_active=True
    )
    m_adv1 = InstitutionMembership.objects.create(
        user=advisor1, institution=inst_a, role=Role.ADVISOR, is_active=True
    )
    InstitutionMembership.objects.create(
        user=coord1, institution=inst_a, role=Role.COORDINATOR, is_active=True
    )
    InstitutionMembership.objects.create(
        user=admin1, institution=inst_a, role=Role.ADMIN, is_active=True
    )
    InstitutionMembership.objects.create(
        user=student_b, institution=inst_b, role=Role.STUDENT, is_active=True
    )

    # Advisor 1 assigned to Student 1 only
    AdvisorAssignment.objects.create(
        institution=inst_a, advisor=m_adv1, student=m_s1, is_active=True
    )

    # Student Records
    rec_s1 = StudentRecord.objects.create(
        institution=inst_a,
        student=student1,
        programme=prog_a,
        pinned_curriculum=curr_v1,
        enrollment_term=term_a,
        status=StudentRecordStatus.ACTIVE,
    )
    rec_s2 = StudentRecord.objects.create(
        institution=inst_a,
        student=student2,
        programme=prog_a,
        pinned_curriculum=curr_v1,
        enrollment_term=term_a,
        status=StudentRecordStatus.ACTIVE,
    )

    # Transcript for S1
    TranscriptEntry.objects.create(
        institution=inst_a,
        student_record=rec_s1,
        course=c101,
        term=term_a,
        grade="A",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("4.00"),
        status=TranscriptEntryStatus.COMPLETED,
        verification_status=VerificationStatus.VERIFIED,
    )

    # Plans
    plan_s1 = Plan.objects.create(
        institution=inst_a,
        student_record=rec_s1,
        curriculum_version=curr_v1,
        name="S1 Degree Plan",
        status=PlanStatus.DRAFT,
    )
    plan_s2 = Plan.objects.create(
        institution=inst_a,
        student_record=rec_s2,
        curriculum_version=curr_v1,
        name="S2 Degree Plan",
        status=PlanStatus.DRAFT,
    )

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "student1": student1,
        "student2": student2,
        "advisor1": advisor1,
        "coord1": coord1,
        "admin1": admin1,
        "student_b": student_b,
        "rec_s1": rec_s1,
        "rec_s2": rec_s2,
        "plan_s1": plan_s1,
        "plan_s2": plan_s2,
        "curr_v1": curr_v1,
    }


@pytest.mark.django_db
class TestEndpointRoleTenantAuthorizationMatrix:
    """Automated matrix testing across 5 security personas & all system modules."""

    def test_anonymous_requests_blocked_from_protected_endpoints(self, auth_matrix_setup):
        client = APIClient()
        rec_id = auth_matrix_setup["rec_s1"].id
        plan_id = auth_matrix_setup["plan_s1"].id

        inst_id = auth_matrix_setup["inst_a"].id
        protected_urls = [
            ("GET", "/api/auth/me/"),
            ("GET", f"/api/institutions/{inst_id}/departments/"),
            ("GET", f"/api/v1/student-records/{rec_id}/"),
            ("GET", f"/api/v1/student-records/{rec_id}/audit/"),
            ("GET", f"/api/v1/plans/{plan_id}/"),
            ("GET", "/api/v1/analytics/overview/"),
            ("GET", "/api/v1/notifications/"),
            ("POST", "/api/v1/assistant/query/"),
            ("GET", f"/api/v1/advising/students/{rec_id}/risk/"),
            ("GET", "/api/v1/career/preferences/"),
        ]

        for method, url in protected_urls:
            if method == "GET":
                resp = client.get(url)
            else:
                resp = client.post(url, {})
            assert resp.status_code in (
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ), f"Expected 401/403 for anonymous on {url}, got {resp.status_code}"

    def test_student_role_authorization_and_isolation(self, auth_matrix_setup):
        client = APIClient()
        client.force_authenticate(user=auth_matrix_setup["student1"])
        rec_s1 = auth_matrix_setup["rec_s1"]
        rec_s2 = auth_matrix_setup["rec_s2"]
        plan_s1 = auth_matrix_setup["plan_s1"]
        plan_s2 = auth_matrix_setup["plan_s2"]

        # Student CAN access own degree audit & plan
        resp_audit = client.get(f"/api/v1/student-records/{rec_s1.id}/audit/")
        assert resp_audit.status_code == status.HTTP_200_OK

        resp_plan = client.get(f"/api/v1/plans/{plan_s1.id}/")
        assert resp_plan.status_code == status.HTTP_200_OK

        # Student CANNOT access another student's degree audit or plan
        resp_other_audit = client.get(f"/api/v1/student-records/{rec_s2.id}/audit/")
        assert resp_other_audit.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

        resp_other_plan = client.get(f"/api/v1/plans/{plan_s2.id}/")
        assert resp_other_plan.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

        # Student CANNOT access institutional analytics reports
        resp_analytics = client.get("/api/v1/analytics/overview/")
        assert resp_analytics.status_code == status.HTTP_403_FORBIDDEN

        # Student CANNOT author or publish curriculum versions
        resp_curr = client.post("/api/v1/programmes/", {"code": "HACK", "name": "Illegal"})
        assert resp_curr.status_code == status.HTTP_403_FORBIDDEN

    def test_advisor_role_scoping_to_assigned_advisees(self, auth_matrix_setup):
        client = APIClient()
        client.force_authenticate(user=auth_matrix_setup["advisor1"])
        rec_s1 = auth_matrix_setup["rec_s1"]
        rec_s2 = auth_matrix_setup["rec_s2"]
        plan_s1 = auth_matrix_setup["plan_s1"]
        plan_s2 = auth_matrix_setup["plan_s2"]

        # Advisor CAN query assigned student's risk profile & audit
        resp_risk = client.get(f"/api/v1/advising/students/{rec_s1.id}/risk/")
        assert resp_risk.status_code == status.HTTP_200_OK

        resp_plan = client.get(f"/api/v1/plans/{plan_s1.id}/")
        assert resp_plan.status_code == status.HTTP_200_OK

        # Advisor CANNOT query unassigned student's risk profile or plan
        resp_other_risk = client.get(f"/api/v1/advising/students/{rec_s2.id}/risk/")
        assert resp_other_risk.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

        resp_other_plan = client.get(f"/api/v1/plans/{plan_s2.id}/")
        assert resp_other_plan.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

        # Advisor CANNOT execute coordinator curriculum publishing
        curr_v1 = auth_matrix_setup["curr_v1"]
        resp_publish = client.post(f"/api/v1/curricula/{curr_v1.id}/publish/")
        assert resp_publish.status_code == status.HTTP_403_FORBIDDEN

    def test_coordinator_administrative_authorization(self, auth_matrix_setup):
        client = APIClient()
        client.force_authenticate(user=auth_matrix_setup["coord1"])

        # Coordinator CAN access institution analytics
        resp_overview = client.get("/api/v1/analytics/overview/")
        assert resp_overview.status_code == status.HTTP_200_OK

        # Coordinator CAN access career taxonomy
        resp_skills = client.get("/api/v1/career/skills/")
        assert resp_skills.status_code == status.HTTP_200_OK

        # Coordinator CAN view all institution plans
        resp_plans = client.get("/api/v1/plans/")
        assert resp_plans.status_code == status.HTTP_200_OK

    def test_strict_cross_tenant_isolation(self, auth_matrix_setup):
        client = APIClient()
        client.force_authenticate(user=auth_matrix_setup["student_b"])
        rec_s1 = auth_matrix_setup["rec_s1"]
        plan_s1 = auth_matrix_setup["plan_s1"]

        # User from Inst B attempting to access Inst A records
        resp_audit = client.get(f"/api/v1/student-records/{rec_s1.id}/audit/")
        assert resp_audit.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

        resp_plan = client.get(f"/api/v1/plans/{plan_s1.id}/")
        assert resp_plan.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

        resp_risk = client.get(f"/api/v1/advising/students/{rec_s1.id}/risk/")
        assert resp_risk.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )
