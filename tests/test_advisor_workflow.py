from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from academic_records.models import AcademicTerm, StudentRecord, StudentRecordStatus
from accounts.models import AdvisorAssignment, InstitutionMembership, Role
from curriculum.models import (
    Course,
    CurriculumStatus,
    CurriculumVersion,
    DegreeType,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupType,
)
from institutions.models import Institution
from planning.models import (
    OverrideImmutabilityError,
    OverrideType,
    PlanReviewDecision,
    PlanStatus,
    PlanVersionStatus,
)
from planning.services.plan_management_service import add_course_to_plan, create_plan
from planning.services.snapshot_service import create_plan_version_snapshot
from planning.services.workflow_service import (
    record_plan_override,
    start_review,
)


@pytest.fixture
def workflow_environment(db):
    inst = Institution.objects.create(name="Advising University", code="ADV_U", domain="advising.edu")
    other_inst = Institution.objects.create(name="Other University", code="OTHER_U", domain="other.edu")

    # Terms
    term_1 = AcademicTerm.objects.create(
        institution=inst,
        code="FA2026",
        name="Fall 2026",
        season="FALL",
        year=2026,
        start_date="2026-08-25",
        end_date="2026-12-15",
    )
    term_2 = AcademicTerm.objects.create(
        institution=inst,
        code="SP2027",
        name="Spring 2027",
        season="SPRING",
        year=2027,
        start_date="2027-01-15",
        end_date="2027-05-15",
    )

    # Course
    course_cs101 = Course.objects.create(
        institution=inst,
        code="CS101",
        title="Intro to CS",
        credits=Decimal("4.00"),
    )

    # Programme & Curriculum
    prog = Programme.objects.create(
        institution=inst,
        name="Software Engineering",
        code="SE",
        degree_type=DegreeType.BACHELOR,
    )
    curr_v1 = CurriculumVersion.objects.create(
        institution=inst,
        programme=prog,
        version_number=1,
        academic_year="2026-2027",
        status=CurriculumStatus.DRAFT,
        total_credits_required=Decimal("120.00"),
        min_cgpa_required=Decimal("5.000"),
    )
    req_group = RequirementGroup.objects.create(
        institution=inst,
        curriculum_version=curr_v1,
        name="Core Software",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("4.00"),
    )
    RequirementGroupCourse.objects.create(
        requirement_group=req_group,
        course=course_cs101,
        is_mandatory=True,
    )
    curr_v1.status = CurriculumStatus.PUBLISHED
    curr_v1.save(update_fields=["status"])


    # Users
    student_user = User.objects.create_user(
        username="student_advisee", email="student@advising.edu", password="Password123!"
    )
    unassigned_student_user = User.objects.create_user(
        username="student_unassigned", email="unassigned@advising.edu", password="Password123!"
    )
    advisor_user = User.objects.create_user(
        username="advisor_alice", email="alice@advising.edu", password="Password123!"
    )
    advisor_bob_user = User.objects.create_user(
        username="advisor_bob", email="bob@advising.edu", password="Password123!"
    )
    coord_user = User.objects.create_user(
        username="coord_carol", email="carol@advising.edu", password="Password123!"
    )
    admin_user = User.objects.create_user(
        username="admin_dan", email="dan@advising.edu", password="Password123!"
    )
    other_advisor_user = User.objects.create_user(
        username="other_advisor", email="other@other.edu", password="Password123!"
    )

    # Memberships
    m_student = InstitutionMembership.objects.create(
        institution=inst, user=student_user, role=Role.STUDENT, is_active=True
    )
    InstitutionMembership.objects.create(
        institution=inst, user=unassigned_student_user, role=Role.STUDENT, is_active=True
    )
    m_advisor = InstitutionMembership.objects.create(
        institution=inst, user=advisor_user, role=Role.ADVISOR, is_active=True
    )
    InstitutionMembership.objects.create(
        institution=inst, user=advisor_bob_user, role=Role.ADVISOR, is_active=True
    )
    InstitutionMembership.objects.create(
        institution=inst, user=coord_user, role=Role.COORDINATOR, is_active=True
    )
    InstitutionMembership.objects.create(
        institution=inst, user=admin_user, role=Role.ADMIN, is_active=True
    )
    InstitutionMembership.objects.create(
        institution=other_inst, user=other_advisor_user, role=Role.ADVISOR, is_active=True
    )

    # Student Records
    rec_assigned = StudentRecord.objects.create(
        institution=inst,
        student=student_user,
        programme=prog,
        pinned_curriculum=curr_v1,
        enrollment_term=term_1,
        expected_graduation_term=term_2,
        status=StudentRecordStatus.ACTIVE,
    )
    rec_unassigned = StudentRecord.objects.create(
        institution=inst,
        student=unassigned_student_user,
        programme=prog,
        pinned_curriculum=curr_v1,
        enrollment_term=term_1,
        expected_graduation_term=term_2,
        status=StudentRecordStatus.ACTIVE,
    )

    # Advisor Assignment: Alice is assigned to student_advisee only
    AdvisorAssignment.objects.create(
        institution=inst,
        advisor=m_advisor,
        student=m_student,
        is_active=True,
    )

    return {
        "inst": inst,
        "other_inst": other_inst,
        "term_1": term_1,
        "term_2": term_2,
        "course_cs101": course_cs101,
        "student_user": student_user,
        "unassigned_student_user": unassigned_student_user,
        "advisor_user": advisor_user,
        "advisor_bob_user": advisor_bob_user,
        "coord_user": coord_user,
        "admin_user": admin_user,
        "other_advisor_user": other_advisor_user,
        "rec_assigned": rec_assigned,
        "rec_unassigned": rec_unassigned,
        "curr_v1": curr_v1,
        "prog": prog,
    }


@pytest.mark.django_db
def test_full_review_lifecycle(workflow_environment):
    env = workflow_environment
    client = APIClient()

    # 1. Student creates draft plan and adds course
    plan = create_plan(student_record=env["rec_assigned"], name="Graduation Plan 2026")
    add_course_to_plan(
        plan=plan,
        course=env["course_cs101"],
        planned_term=env["term_1"],
        term_index=1,
    )
    assert plan.status == PlanStatus.DRAFT

    # 2. Student submits plan snapshot v1
    client.force_authenticate(user=env["student_user"])
    submit_res = client.post(
        f"/api/v1/plans/{plan.id}/submit/",
        {"submission_note": "Please review my core software plan."},
        format="json",
    )
    assert submit_res.status_code == status.HTTP_201_CREATED
    plan.refresh_from_db()
    assert plan.status == PlanStatus.SUBMITTED
    v1 = plan.versions.get(version_number=1)
    assert v1.status == PlanVersionStatus.SUBMITTED

    # 3. Advisor inspects review queue
    client.force_authenticate(user=env["advisor_user"])
    queue_res = client.get("/api/v1/advising/queue/")
    assert queue_res.status_code == status.HTTP_200_OK
    queue_data = queue_res.data
    assert len(queue_data) == 1
    assert queue_data[0]["plan_id"] == str(plan.id)
    assert queue_data[0]["student_username"] == "student_advisee"
    assert queue_data[0]["status"] == "SUBMITTED"

    # 4. Advisor starts review
    start_res = client.post(
        f"/api/v1/plans/{plan.id}/start-review/",
        {"expected_row_version": plan.row_version},
        format="json",
    )
    assert start_res.status_code == status.HTTP_200_OK
    plan.refresh_from_db()
    v1.refresh_from_db()
    assert plan.status == PlanStatus.UNDER_REVIEW
    assert v1.status == PlanVersionStatus.UNDER_REVIEW

    # 5. Advisor returns plan for revision with required comments
    # Without comments: fails
    no_comment_res = client.post(
        f"/api/v1/plans/{plan.id}/return/",
        {"comments": "   "},
        format="json",
    )
    assert no_comment_res.status_code == status.HTTP_400_BAD_REQUEST

    return_res = client.post(
        f"/api/v1/plans/{plan.id}/return/",
        {"comments": "Please distribute CS101 into Term 2 to balance semester load."},
        format="json",
    )
    assert return_res.status_code == status.HTTP_200_OK
    plan.refresh_from_db()
    v1.refresh_from_db()
    assert plan.status == PlanStatus.RETURNED
    assert v1.status == PlanVersionStatus.RETURNED

    # 6. Student revises plan and submits v2
    client.force_authenticate(user=env["student_user"])
    submit_v2_res = client.post(
        f"/api/v1/plans/{plan.id}/submit/",
        {"submission_note": "Updated course scheduling per advisor feedback."},
        format="json",
    )
    assert submit_v2_res.status_code == status.HTTP_201_CREATED
    plan.refresh_from_db()
    assert plan.status == PlanStatus.SUBMITTED
    v2 = plan.versions.get(version_number=2)
    assert v2.status == PlanVersionStatus.SUBMITTED

    # 7. Advisor starts review of v2 and approves
    client.force_authenticate(user=env["advisor_user"])
    client.post(f"/api/v1/plans/{plan.id}/start-review/", format="json")
    approve_res = client.post(
        f"/api/v1/plans/{plan.id}/approve/",
        {"comments": "Approved. Schedule meets load guidelines."},
        format="json",
    )
    assert approve_res.status_code == status.HTTP_200_OK
    plan.refresh_from_db()
    v2.refresh_from_db()
    assert plan.status == PlanStatus.APPROVED
    assert v2.status == PlanVersionStatus.APPROVED

    # 8. Advisor records authoritative override
    override_res = client.post(
        f"/api/v1/plans/{plan.id}/override/",
        {
            "override_type": "PREREQUISITE_OVERRIDE",
            "justification": "Student has prior industry software engineering experience verified by faculty.",
        },
        format="json",
    )
    assert override_res.status_code == status.HTTP_201_CREATED
    assert override_res.data["override_type"] == "PREREQUISITE_OVERRIDE"

    # 9. Verify audit logs
    audit_res = client.get(f"/api/v1/plans/{plan.id}/audit-history/")
    assert audit_res.status_code == status.HTTP_200_OK
    actions = [log["action"] for log in audit_res.data]
    assert "RECORD_OVERRIDE" in actions
    assert "PLAN_APPROVE" in actions
    assert "PLAN_RETURN" in actions


@pytest.mark.django_db
def test_advisor_review_authorization_and_scoping(workflow_environment):
    env = workflow_environment
    client = APIClient()

    plan = create_plan(student_record=env["rec_assigned"], name="Scoping Test Plan")
    client.force_authenticate(user=env["student_user"])
    client.post(f"/api/v1/plans/{plan.id}/submit/", {"submission_note": "ready"}, format="json")

    # 1. Student cannot start review or approve
    student_action = client.post(f"/api/v1/plans/{plan.id}/approve/", format="json")
    assert student_action.status_code == status.HTTP_403_FORBIDDEN

    # 2. Student cannot record override
    student_override = client.post(
        f"/api/v1/plans/{plan.id}/override/",
        {
            "override_type": "PREREQUISITE_OVERRIDE",
            "justification": "Self-approved prerequisite waiver for CS101 course.",
        },
        format="json",
    )
    assert student_override.status_code == status.HTTP_403_FORBIDDEN

    # 3. Unassigned advisor (Bob) cannot review Alice's advisee
    client.force_authenticate(user=env["advisor_bob_user"])
    bob_res = client.post(f"/api/v1/plans/{plan.id}/start-review/", format="json")
    # API view scopes queryset so unassigned advisee plan is concealed (404)
    assert bob_res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    # Direct service check raises PermissionDenied
    from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
    with pytest.raises(DjangoPermissionDenied):
        start_review(plan=plan, version=plan.versions.first(), advisor=env["advisor_bob_user"])

    # 4. Cross-tenant advisor cannot access or review
    client.force_authenticate(user=env["other_advisor_user"])
    other_res = client.post(f"/api/v1/plans/{plan.id}/start-review/", format="json")
    assert other_res.status_code == status.HTTP_404_NOT_FOUND

    # 5. Coordinator CAN review without explicit AdvisorAssignment
    client.force_authenticate(user=env["coord_user"])
    coord_start = client.post(f"/api/v1/plans/{plan.id}/start-review/", format="json")
    assert coord_start.status_code == status.HTTP_200_OK

    coord_approve = client.post(
        f"/api/v1/plans/{plan.id}/approve/",
        {"comments": "Coordinator institution-wide approval."},
        format="json",
    )
    assert coord_approve.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_override_immutability_and_transcript_protection(workflow_environment):
    env = workflow_environment
    client = APIClient()

    plan = create_plan(student_record=env["rec_assigned"], name="Override Protection Plan")
    create_plan_version_snapshot(plan=plan, submitted_by=env["student_user"])
    v1 = plan.versions.get(version_number=1)

    # 1. Justification < 15 characters rejected
    client.force_authenticate(user=env["advisor_user"])
    short_res = client.post(
        f"/api/v1/plans/{plan.id}/override/",
        {
            "override_type": "PREREQUISITE_OVERRIDE",
            "justification": "Too short",
        },
        format="json",
    )
    assert short_res.status_code == status.HTTP_400_BAD_REQUEST

    # 2. Record valid override
    valid_justification = "Approved based on relevant transfer credit evaluation."
    override = record_plan_override(
        plan=plan,
        version=v1,
        actor=env["advisor_user"],
        override_type=OverrideType.CREDIT_CEILING_OVERRIDE,
        justification=valid_justification,
    )
    assert override.id is not None

    # 3. Attempting to update OverrideEvent raises OverrideImmutabilityError
    with pytest.raises(OverrideImmutabilityError):
        override.justification = "Attempted tampering of justification."
        override.save()

    # 4. Attempting to delete OverrideEvent raises OverrideImmutabilityError
    with pytest.raises(OverrideImmutabilityError):
        override.delete()

    # 5. Overrides NEVER alter StudentRecord or TranscriptEntry
    env["rec_assigned"].refresh_from_db()
    assert env["rec_assigned"].pinned_curriculum == env["curr_v1"]
    assert env["rec_assigned"].transcript_entries.count() == 0


@pytest.mark.django_db
def test_optimistic_concurrency_control_on_review(workflow_environment):
    env = workflow_environment
    client = APIClient()

    plan = create_plan(student_record=env["rec_assigned"], name="OCC Review Plan")
    create_plan_version_snapshot(plan=plan, submitted_by=env["student_user"])
    plan.refresh_from_db()
    current_version = plan.row_version

    client.force_authenticate(user=env["advisor_user"])
    # Stale row version returns 409 Conflict
    conflict_res = client.post(
        f"/api/v1/plans/{plan.id}/start-review/",
        {"expected_row_version": current_version + 99},
        format="json",
    )
    assert conflict_res.status_code == status.HTTP_409_CONFLICT
    assert conflict_res.data["code"] == "CONCURRENCY_CONFLICT"


@pytest.mark.django_db
def test_idempotent_review_decisions(workflow_environment):
    env = workflow_environment
    client = APIClient()

    plan = create_plan(student_record=env["rec_assigned"], name="Idempotency Plan")
    create_plan_version_snapshot(plan=plan, submitted_by=env["student_user"])

    client.force_authenticate(user=env["advisor_user"])
    client.post(f"/api/v1/plans/{plan.id}/start-review/", format="json")

    idempotency_key = "idemp-key-abc-12345678"
    first_res = client.post(
        f"/api/v1/plans/{plan.id}/approve/",
        {
            "comments": "First approval submission.",
            "idempotency_key": idempotency_key,
        },
        format="json",
    )
    assert first_res.status_code == status.HTTP_200_OK
    decision_id = first_res.data["id"]

    # Second identical submission with same idempotency key returns same decision
    second_res = client.post(
        f"/api/v1/plans/{plan.id}/approve/",
        {
            "comments": "Duplicate replay submission.",
            "idempotency_key": idempotency_key,
        },
        format="json",
    )
    assert second_res.status_code == status.HTTP_200_OK
    assert second_res.data["id"] == decision_id
    assert PlanReviewDecision.objects.filter(idempotency_key=idempotency_key).count() == 1


@pytest.mark.django_db
def test_version_isolation_on_approval(workflow_environment):
    env = workflow_environment
    client = APIClient()

    plan = create_plan(student_record=env["rec_assigned"], name="Isolation Plan")
    create_plan_version_snapshot(plan=plan, submitted_by=env["student_user"])
    v1 = plan.versions.get(version_number=1)

    # Advisor approves v1
    client.force_authenticate(user=env["advisor_user"])
    client.post(f"/api/v1/plans/{plan.id}/start-review/", format="json")
    client.post(f"/api/v1/plans/{plan.id}/approve/", format="json")

    v1.refresh_from_db()
    assert v1.status == PlanVersionStatus.APPROVED

    # Student creates revision v2
    client.force_authenticate(user=env["student_user"])
    v2_res = client.post(
        f"/api/v1/plans/{plan.id}/submit/",
        {"submission_note": "Version 2 modifications."},
        format="json",
    )
    assert v2_res.status_code == status.HTTP_201_CREATED

    v2 = plan.versions.get(version_number=2)
    # Crucial invariant: Version 2 is NOT approved! Approval of v1 does NOT cascade to v2.
    assert v2.status == PlanVersionStatus.SUBMITTED
