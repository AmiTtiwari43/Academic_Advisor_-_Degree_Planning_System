import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from academic_records.models import (
    AcademicTerm,
    StudentRecord,
    StudentRecordStatus,
    TermSeason,
    TranscriptEntry,
)
from accounts.models import (
    AdvisorAssignment,
    InstitutionMembership,
    Role,
)
from advising.models import OverallRiskLevel, StudentRiskProfile
from analytics.services import (
    generate_report_csv,
    get_advisor_workload_report,
    get_analytics_overview_summary,
    get_approval_turnaround_report,
    get_elective_demand_report,
    get_plan_approval_funnel_report,
    get_prerequisite_blockers_report,
    get_programme_progress_report,
    get_risk_distribution_report,
    sanitize_csv_cell,
)
from curriculum.models import (
    Course,
    CourseOffering,
    CurriculumStatus,
    CurriculumVersion,
    DeliveryMode,
    Programme,
)
from institutions.models import Institution
from planning.models import (
    Plan,
    PlanItem,
    PlanReviewDecision,
    PlanStatus,
    PlanVersion,
    PlanVersionStatus,
    ReviewAction,
)


@pytest.fixture
def analytics_setup(db):
    inst1 = Institution.objects.create(name="Analytics University", code="AU", domain="au.edu")
    inst2 = Institution.objects.create(name="Rival University", code="RU", domain="ru.edu")

    term_fall2026 = AcademicTerm.objects.create(
        institution=inst1,
        code="FA2026",
        name="Fall 2026",
        season=TermSeason.FALL,
        year=2026,
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 12, 20),
    )
    term_spring2027 = AcademicTerm.objects.create(
        institution=inst1,
        code="SP2027",
        name="Spring 2027",
        season=TermSeason.SPRING,
        year=2027,
        start_date=datetime.date(2027, 1, 15),
        end_date=datetime.date(2027, 5, 20),
    )

    prog_cs = Programme.objects.create(
        institution=inst1,
        code="CS-BS",
        name="Bachelor of Science in Computer Science",
    )
    prog_math = Programme.objects.create(
        institution=inst1,
        code="MATH-BS",
        name="Bachelor of Science in Mathematics",
    )

    curriculum_cs = CurriculumVersion.objects.create(
        institution=inst1,
        programme=prog_cs,
        version_number=1,
        status=CurriculumStatus.PUBLISHED,
        academic_year="2026-2027",
        total_credits_required=Decimal("120.00"),
    )



    course_cs101 = Course.objects.create(institution=inst1, code="CS101", title="Intro to CS", credits=Decimal("4.00"))
    course_cs201 = Course.objects.create(institution=inst1, code="CS201", title="Data Structures", credits=Decimal("4.00"))
    course_cs301 = Course.objects.create(institution=inst1, code="CS301", title="Algorithms", credits=Decimal("4.00"))
    course_ai401 = Course.objects.create(institution=inst1, code="AI401", title="Artificial Intelligence", credits=Decimal("4.00"))


    # Users
    u_admin = User.objects.create_user("admin_user", "admin@u.edu", "pass123")
    u_coord = User.objects.create_user("coord_user", "coord@u.edu", "pass123")
    u_advisor = User.objects.create_user("advisor_user", "adv@u.edu", "pass123")
    u_stu1 = User.objects.create_user("stu1_user", "stu1@u.edu", "pass123")
    u_stu2 = User.objects.create_user("stu2_user", "stu2@u.edu", "pass123")
    u_stu3 = User.objects.create_user("stu3_user", "stu3@u.edu", "pass123")
    u_rival = User.objects.create_user("rival_user", "rival@u.edu", "pass123")

    InstitutionMembership.objects.create(institution=inst1, user=u_admin, role=Role.ADMIN, is_active=True)
    InstitutionMembership.objects.create(institution=inst1, user=u_coord, role=Role.COORDINATOR, is_active=True)
    mem_adv = InstitutionMembership.objects.create(institution=inst1, user=u_advisor, role=Role.ADVISOR, is_active=True)
    mem_stu1 = InstitutionMembership.objects.create(institution=inst1, user=u_stu1, role=Role.STUDENT, is_active=True)
    mem_stu2 = InstitutionMembership.objects.create(institution=inst1, user=u_stu2, role=Role.STUDENT, is_active=True)
    InstitutionMembership.objects.create(institution=inst1, user=u_stu3, role=Role.STUDENT, is_active=True)
    InstitutionMembership.objects.create(institution=inst2, user=u_rival, role=Role.ADMIN, is_active=True)

    # Advisor assignment
    AdvisorAssignment.objects.create(institution=inst1, advisor=mem_adv, student=mem_stu1, is_active=True)
    AdvisorAssignment.objects.create(institution=inst1, advisor=mem_adv, student=mem_stu2, is_active=True)

    # Student records
    sr1 = StudentRecord.objects.create(
        institution=inst1,
        student=u_stu1,
        programme=prog_cs,
        pinned_curriculum=curriculum_cs,
        enrollment_term=term_fall2026,
        cached_cgpa=Decimal("3.80"),
        cached_total_credits=Decimal("110.00"),  # Near completion (110 / 120 = 91.6%)
        status=StudentRecordStatus.ACTIVE,
    )
    sr2 = StudentRecord.objects.create(
        institution=inst1,
        student=u_stu2,
        programme=prog_cs,
        pinned_curriculum=curriculum_cs,
        enrollment_term=term_fall2026,
        cached_cgpa=Decimal("2.90"),
        cached_total_credits=Decimal("45.00"),  # Bracket 26-50% (45 / 120 = 37.5%)
        status=StudentRecordStatus.ACTIVE,
    )
    sr3 = StudentRecord.objects.create(
        institution=inst1,
        student=u_stu3,
        programme=prog_cs,
        pinned_curriculum=curriculum_cs,
        enrollment_term=term_fall2026,
        cached_cgpa=Decimal("2.10"),
        cached_total_credits=Decimal("15.00"),  # Bracket 0-25% (15 / 120 = 12.5%)
        status=StudentRecordStatus.ACTIVE,
    )

    # Risk profiles
    StudentRiskProfile.objects.create(
        institution=inst1,
        student_record=sr1,
        overall_risk_level=OverallRiskLevel.LOW,
        active_risk_count=0,
    )
    StudentRiskProfile.objects.create(
        institution=inst1,
        student_record=sr2,
        overall_risk_level=OverallRiskLevel.HIGH,
        active_risk_count=2,
        critical_risk_count=1,
        warning_risk_count=1,
    )
    StudentRiskProfile.objects.create(
        institution=inst1,
        student_record=sr3,
        overall_risk_level=OverallRiskLevel.CRITICAL,
        active_risk_count=3,
        critical_risk_count=2,
        warning_risk_count=1,
    )

    # Failed attempts for prerequisite blockers
    TranscriptEntry.objects.create(
        institution=inst1,
        student_record=sr2,
        course=course_cs201,
        term=term_fall2026,
        status="FAILED",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("0.00"),
        attempt_number=1,
    )
    TranscriptEntry.objects.create(
        institution=inst1,
        student_record=sr3,
        course=course_cs201,
        term=term_fall2026,
        status="FAILED",
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("0.00"),
        attempt_number=1,
    )

    # Plans and turnaround
    plan1 = Plan.objects.create(
        institution=inst1,
        student_record=sr1,
        curriculum_version=curriculum_cs,
        name="Graduation Plan 1",
        status=PlanStatus.APPROVED,
    )
    submission_time = timezone.now() - datetime.timedelta(hours=10)
    pv1 = PlanVersion.objects.create(
        institution=inst1,
        plan=plan1,
        version_number=1,
        status=PlanVersionStatus.APPROVED,
        submitted_by=u_stu1,
        submitted_at=submission_time,
        snapshot_data={"courses": ["AI401"]},
    )
    PlanVersion.objects.filter(id=pv1.id).update(submitted_at=submission_time)
    PlanReviewDecision.objects.create(
        institution=inst1,
        plan=plan1,
        plan_version=pv1,
        reviewer=u_advisor,
        action=ReviewAction.APPROVE,
        from_status=PlanStatus.UNDER_REVIEW,
        to_status=PlanStatus.APPROVED,
        comments="Plan approved with flying colors.",
    )

    plan2 = Plan.objects.create(
        institution=inst1,
        student_record=sr2,
        curriculum_version=curriculum_cs,
        name="Plan 2 Submitted",
        status=PlanStatus.SUBMITTED,
    )
    PlanVersion.objects.create(
        institution=inst1,
        plan=plan2,
        version_number=1,
        status=PlanVersionStatus.SUBMITTED,
        submitted_by=u_stu2,
        submitted_at=timezone.now() - datetime.timedelta(hours=2),
        snapshot_data={},
    )



    plan3 = Plan.objects.create(
        institution=inst1,
        student_record=sr3,
        curriculum_version=curriculum_cs,
        name="Plan 3 Draft",
        status=PlanStatus.DRAFT,
    )

    # Plan items for elective demand
    PlanItem.objects.create(
        institution=inst1,
        plan=plan1,
        course=course_ai401,
        planned_term=term_spring2027,
        term_index=1,
        position=1,
    )
    PlanItem.objects.create(
        institution=inst1,
        plan=plan2,
        course=course_ai401,
        planned_term=term_spring2027,
        term_index=1,
        position=1,
    )


    # Course offering
    CourseOffering.objects.create(
        institution=inst1,
        course=course_ai401,
        academic_term="SPRING",
        academic_year="2027",
        capacity=1,  # Capacity is 1, but demand is 2 -> deficit of 1!
        is_offered=True,
        delivery_mode=DeliveryMode.IN_PERSON,
    )

    return {
        "inst1": inst1,
        "inst2": inst2,
        "u_admin": u_admin,
        "u_coord": u_coord,
        "u_advisor": u_advisor,
        "u_stu1": u_stu1,
        "u_rival": u_rival,
        "course_cs201": course_cs201,
        "course_ai401": course_ai401,
    }


@pytest.mark.django_db
def test_programme_progress_report_aggregations(analytics_setup):
    inst1 = analytics_setup["inst1"]
    report = get_programme_progress_report(inst1)

    assert report["report"] == "programme_progress"
    assert report["total_students_enrolled"] == 3
    assert len(report["items"]) == 1

    cs_item = report["items"][0]
    assert cs_item["programme_code"] == "CS-BS"
    assert cs_item["total_students"] == 3
    # Average credits = (110 + 45 + 15) / 3 = 170 / 3 = 56.666... -> 56.7
    assert cs_item["avg_earned_credits"] == 56.7
    # Average GPA = (3.80 + 2.90 + 2.10) / 3 = 8.80 / 3 = 2.93
    assert cs_item["avg_cgpa"] == 2.93
    # Brackets:
    # sr1 (110 cr): 76-100% and near completion
    # sr2 (45 cr): 26-50%
    # sr3 (15 cr): 0-25%
    assert cs_item["bracket_0_25"] == 1
    assert cs_item["bracket_26_50"] == 1
    assert cs_item["bracket_51_75"] == 0
    assert cs_item["bracket_76_100"] == 1
    assert cs_item["near_completion"] == 1


@pytest.mark.django_db
def test_prerequisite_blockers_report(analytics_setup):
    inst1 = analytics_setup["inst1"]
    report = get_prerequisite_blockers_report(inst1)

    assert report["report"] == "prerequisite_blockers"
    assert report["total_blockers_identified"] >= 1

    top_blocker = report["items"][0]
    assert top_blocker["course_code"] == "CS201"
    assert top_blocker["impacted_students_count"] == 2
    assert top_blocker["total_unpassed_attempts"] == 2


@pytest.mark.django_db
def test_advisor_workload_report(analytics_setup):
    inst1 = analytics_setup["inst1"]
    u_advisor = analytics_setup["u_advisor"]

    report = get_advisor_workload_report(inst1, advisor_id=str(u_advisor.id))

    assert report["report"] == "advisor_workload"
    assert report["total_advisors"] == 1
    assert report["total_active_advisee_assignments"] == 2

    adv_item = report["items"][0]
    assert adv_item["advisor_username"] == "advisor_user"
    assert adv_item["assigned_advisees_count"] == 2
    # sr1 approved (not pending), sr2 submitted (pending) -> 1 pending
    assert adv_item["pending_plans_count"] == 1
    assert adv_item["completed_reviews_count"] == 1
    # Risk among advisees: sr1=LOW, sr2=HIGH
    assert adv_item["high_risk_advisees"] == 1
    assert adv_item["low_risk_advisees"] == 1
    assert adv_item["critical_risk_advisees"] == 0


@pytest.mark.django_db
def test_approval_turnaround_report(analytics_setup):
    inst1 = analytics_setup["inst1"]
    report = get_approval_turnaround_report(inst1)

    assert report["report"] == "approval_turnaround"
    assert report["total_decisions"] == 1
    # Submitted ~10 hours before decision
    assert report["avg_turnaround_hours"] >= 9.5
    assert len(report["reviewer_breakdown"]) == 1
    assert report["reviewer_breakdown"][0]["reviewer_name"] == "advisor_user"


@pytest.mark.django_db
def test_plan_approval_funnel_report(analytics_setup):
    inst1 = analytics_setup["inst1"]
    report = get_plan_approval_funnel_report(inst1)

    assert report["report"] == "plan_funnel"
    assert report["total_plans"] == 3
    assert report["stages"]["draft"] == 1
    assert report["stages"]["submitted"] == 1
    assert report["stages"]["approved"] == 1
    assert report["conversion_rates"]["submission_rate_pct"] == 66.7
    assert report["conversion_rates"]["approval_rate_pct"] == 100.0


@pytest.mark.django_db
def test_risk_distribution_report(analytics_setup):
    inst1 = analytics_setup["inst1"]
    report = get_risk_distribution_report(inst1)

    assert report["report"] == "risk_distribution"
    assert report["total_students_assessed"] == 3
    assert report["risk_levels"]["critical"] == 1
    assert report["risk_levels"]["high"] == 1
    assert report["risk_levels"]["low"] == 1
    assert report["risk_levels"]["medium"] == 0
    assert report["aggregate_indicators"]["total_active_indicators"] == 5


@pytest.mark.django_db
def test_elective_demand_report(analytics_setup):
    inst1 = analytics_setup["inst1"]
    report = get_elective_demand_report(inst1)

    assert report["report"] == "elective_demand"
    assert report["total_items_projected"] == 1

    item = report["items"][0]
    assert item["course_code"] == "AI401"
    assert item["student_demand_count"] == 2
    assert item["scheduled_capacity"] == 1
    assert item["projected_capacity_deficit"] == 1


@pytest.mark.django_db
def test_analytics_overview_summary(analytics_setup):
    inst1 = analytics_setup["inst1"]
    overview = get_analytics_overview_summary(inst1)

    assert overview["total_active_students"] == 3
    assert overview["total_plans"] == 3
    assert overview["plans_pending_review"] == 1
    # sr2=HIGH, sr3=CRITICAL -> 2 students
    assert overview["critical_or_high_risk_students"] == 2
    assert len(overview["top_bottlenecks"]) >= 1


def test_sanitize_csv_cell_and_formula_injection():
    # Dangerous formula inputs (CWE-1236)
    assert sanitize_csv_cell("=CMD|' /C calc'!A0") == "'=CMD|' /C calc'!A0"
    assert sanitize_csv_cell("+12345") == "'+12345"
    assert sanitize_csv_cell("-12345") == "'-12345"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("\tTabbed") == "'\tTabbed"
    assert sanitize_csv_cell("\rReturn") == "'\rReturn"

    # Safe inputs
    assert sanitize_csv_cell("Computer Science") == "Computer Science"
    assert sanitize_csv_cell(123) == "123"
    assert sanitize_csv_cell(Decimal("3.85")) == "3.85"
    assert sanitize_csv_cell(None) == ""

    # Generate CSV with bounding
    headers = ["Title", "Value"]
    rows = [["Item 1", "=1+1"], ["Item 2", "Regular"]]
    csv_str = generate_report_csv("Test Report", headers, rows, max_rows=1)
    assert "'=1+1" in csv_str
    assert "[TRUNCATED]" in csv_str


@pytest.mark.django_db
def test_role_based_permissions_and_scoping(analytics_setup):
    client = APIClient()
    inst1 = analytics_setup["inst1"]
    u_stu1 = analytics_setup["u_stu1"]
    u_advisor = analytics_setup["u_advisor"]
    u_coord = analytics_setup["u_coord"]
    u_admin = analytics_setup["u_admin"]

    # 1. Student accessing analytics is strictly denied (403 Forbidden)
    client.force_authenticate(user=u_stu1)
    resp = client.get("/api/analytics/overview/", HTTP_X_INSTITUTION_ID=str(inst1.id))
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    resp = client.get("/api/analytics/programme-progress/", HTTP_X_INSTITUTION_ID=str(inst1.id))
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    # 2. Advisor accessing analytics is permitted (200 OK)
    client.force_authenticate(user=u_advisor)
    resp = client.get("/api/analytics/advisor-workload/", HTTP_X_INSTITUTION_ID=str(inst1.id))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["total_advisors"] == 1

    # 3. Coordinator accessing analytics is permitted (200 OK)
    client.force_authenticate(user=u_coord)
    resp = client.get("/api/analytics/overview/", HTTP_X_INSTITUTION_ID=str(inst1.id))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["total_active_students"] == 3

    # 4. Admin accessing analytics is permitted (200 OK)
    client.force_authenticate(user=u_admin)
    resp = client.get("/api/analytics/plan-funnel/", HTTP_X_INSTITUTION_ID=str(inst1.id))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["total_plans"] == 3


@pytest.mark.django_db
def test_csv_export_endpoint_with_formula_escaping(analytics_setup):
    client = APIClient()
    inst1 = analytics_setup["inst1"]
    u_coord = analytics_setup["u_coord"]

    client.force_authenticate(user=u_coord)
    resp = client.get(
        "/api/analytics/programme-progress/?format=csv",
        HTTP_X_INSTITUTION_ID=str(inst1.id),
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp["Content-Type"] == "text/csv"
    assert "attachment; filename=" in resp["Content-Disposition"]
    csv_text = resp.content.decode("utf-8")
    assert "Programme Code,Programme Name,Min Credits" in csv_text
    assert "CS-BS" in csv_text


@pytest.mark.django_db
def test_cross_tenant_isolation_returns_404(analytics_setup):
    client = APIClient()
    inst1 = analytics_setup["inst1"]
    u_rival = analytics_setup["u_rival"]  # Admin of inst2, requesting inst1 analytics

    client.force_authenticate(user=u_rival)
    resp = client.get("/api/analytics/overview/", HTTP_X_INSTITUTION_ID=str(inst1.id))
    # Must yield 404 Not Found to prevent data existence leakage across institutions
    assert resp.status_code == status.HTTP_404_NOT_FOUND
