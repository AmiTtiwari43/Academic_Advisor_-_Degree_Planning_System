import datetime

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from academic_records.models import (
    AcademicTerm,
    StudentRecord,
    StudentRecordStatus,
    TermSeason,
)
from accounts.models import AdvisorAssignment, InstitutionMembership, Role
from curriculum.models import CurriculumStatus, CurriculumVersion, Programme
from institutions.models import Institution
from notifications.models import (
    DeliveryStatus,
    Notification,
    NotificationEventType,
    ReadStatus,
)
from notifications.services import (
    build_deduplication_key,
    create_notification,
    get_unread_notifications_count,
    mark_all_notifications_as_read,
    mark_notification_as_read,
    notify_advisor_queue_summary,
    notify_plan_review_decision,
    notify_plan_submitted,
    notify_prerequisite_risk_alert,
    sanitize_preview_text,
)
from planning.models import Plan, PlanStatus

User = get_user_model()


@pytest.fixture
def notifications_setup(db):
    inst1 = Institution.objects.create(name="Apex Tech", code="AT", domain="apextech.edu")
    inst2 = Institution.objects.create(name="Rival University", code="RU", domain="ru.edu")

    # Terms
    term_fall = AcademicTerm.objects.create(
        institution=inst1,
        code="2026-FALL",
        name="Fall 2026",
        season=TermSeason.FALL,
        year=2026,
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 12, 15),
    )

    # Programmes & Curriculum
    prog = Programme.objects.create(institution=inst1, code="CS-BS", name="BS Computer Science")
    curr_v1 = CurriculumVersion.objects.create(
        institution=inst1, programme=prog, version_number=1, status=CurriculumStatus.PUBLISHED
    )

    # Users for Inst 1
    student = User.objects.create_user(username="student1", password="password123")
    advisor = User.objects.create_user(username="advisor1", password="password123")
    other_student = User.objects.create_user(username="student2", password="password123")

    # User for Inst 2
    inst2_user = User.objects.create_user(username="inst2_student", password="password123")

    m_student = InstitutionMembership.objects.create(
        user=student, institution=inst1, role=Role.STUDENT, is_active=True
    )
    m_advisor = InstitutionMembership.objects.create(
        user=advisor, institution=inst1, role=Role.ADVISOR, is_active=True
    )
    InstitutionMembership.objects.create(
        user=other_student, institution=inst1, role=Role.STUDENT, is_active=True
    )
    InstitutionMembership.objects.create(
        user=inst2_user, institution=inst2, role=Role.STUDENT, is_active=True
    )

    AdvisorAssignment.objects.create(
        institution=inst1,
        advisor=m_advisor,
        student=m_student,
        is_active=True,
    )

    student_rec = StudentRecord.objects.create(
        institution=inst1,
        student=student,
        programme=prog,
        pinned_curriculum=curr_v1,
        enrollment_term=term_fall,
        status=StudentRecordStatus.ACTIVE,
    )

    plan = Plan.objects.create(
        institution=inst1,
        student_record=student_rec,
        curriculum_version=curr_v1,
        name="Degree Plan Fall 2026",
        status=PlanStatus.DRAFT,
    )

    return {
        "inst1": inst1,
        "inst2": inst2,
        "student": student,
        "advisor": advisor,
        "other_student": other_student,
        "inst2_user": inst2_user,
        "student_rec": student_rec,
        "plan": plan,
    }


@pytest.mark.django_db
class TestNotificationEngineDeduplication:
    """Verifies deduplication guarantees and idempotency."""

    def test_notification_deduplication_retry_produces_single_record(self, notifications_setup):
        inst = notifications_setup["inst1"]
        recipient = notifications_setup["student"]

        notif1, created1 = create_notification(
            institution=inst,
            recipient=recipient,
            event_type=NotificationEventType.REGISTRATION_REMINDER,
            subject="Registration is Open",
            preview="Registration for Fall 2026 is now open.",
            subject_id="fall-2026-reg",
            window="2026-fall",
        )
        assert created1 is True
        assert notif1.read_status == ReadStatus.UNREAD
        assert notif1.delivery_status == DeliveryStatus.DELIVERED

        # Retry with identical parameters
        notif2, created2 = create_notification(
            institution=inst,
            recipient=recipient,
            event_type=NotificationEventType.REGISTRATION_REMINDER,
            subject="Registration is Open (Retry)",
            preview="Registration for Fall 2026 is now open.",
            subject_id="fall-2026-reg",
            window="2026-fall",
        )
        assert created2 is False
        assert notif1.id == notif2.id

        # Total notifications in DB must be exactly 1
        total = Notification.objects.filter(
            recipient=recipient,
            event_type=NotificationEventType.REGISTRATION_REMINDER,
        ).count()
        assert total == 1

    def test_deduplication_key_deterministic(self, notifications_setup):
        inst_id = notifications_setup["inst1"].id
        user_id = notifications_setup["student"].id

        key1 = build_deduplication_key(inst_id, user_id, "EVENT_A", "SUBJ_1", "WIN_1")
        key2 = build_deduplication_key(inst_id, user_id, "EVENT_A", "SUBJ_1", "WIN_1")
        assert key1 == key2
        assert len(key1) == 64

        key_diff_subj = build_deduplication_key(inst_id, user_id, "EVENT_A", "SUBJ_2", "WIN_1")
        assert key1 != key_diff_subj


@pytest.mark.django_db
class TestNotificationPrivacySanitization:
    """Verifies sensitive academic details are masked in preview texts."""

    def test_preview_sanitization_removes_grades_and_gpas(self):
        raw_text_grade = "Your semester summary: Grade: A+ in CS101 and received F in MATH201."
        sanitized_grade = sanitize_preview_text(raw_text_grade)
        assert "Grade: A+" not in sanitized_grade
        assert "received F" not in sanitized_grade
        assert "academic performance update" in sanitized_grade

        raw_text_gpa = "Academic update: GPA: 2.10 and CGPA 1.95 recorded."
        sanitized_gpa = sanitize_preview_text(raw_text_gpa)
        assert "GPA: 2.10" not in sanitized_gpa
        assert "CGPA 1.95" not in sanitized_gpa
        assert "academic standing" in sanitized_gpa

    def test_notification_creation_sanitizes_preview(self, notifications_setup):
        inst = notifications_setup["inst1"]
        recipient = notifications_setup["student"]

        notif, _ = create_notification(
            institution=inst,
            recipient=recipient,
            event_type=NotificationEventType.PLAN_RETURNED,
            subject="Plan Returned",
            preview="Review notes: failed with F, current CGPA 1.80 requires discussion.",
        )
        assert "failed with F" not in notif.preview
        assert "CGPA 1.80" not in notif.preview
        assert "academic performance update" in notif.preview


@pytest.mark.django_db
class TestNotificationReadStatusAndServices:
    """Verifies marking as read, counting, and tenant scoping."""

    def test_mark_single_notification_read(self, notifications_setup):
        inst = notifications_setup["inst1"]
        recipient = notifications_setup["student"]

        notif, _ = create_notification(
            institution=inst,
            recipient=recipient,
            event_type=NotificationEventType.PLAN_APPROVED,
            subject="Plan Approved",
            preview="Your plan has been approved.",
        )
        assert notif.read_status == ReadStatus.UNREAD
        assert notif.read_at is None

        read_notif = mark_notification_as_read(notif.id, recipient)
        assert read_notif.read_status == ReadStatus.READ
        assert read_notif.read_at is not None

    def test_mark_all_notifications_as_read(self, notifications_setup):
        inst = notifications_setup["inst1"]
        recipient = notifications_setup["student"]

        for i in range(3):
            create_notification(
                institution=inst,
                recipient=recipient,
                event_type=NotificationEventType.PLAN_SUBMITTED,
                subject=f"Submission {i}",
                preview=f"Submission preview {i}",
                subject_id=f"sub-{i}",
            )

        unread_before = get_unread_notifications_count(recipient, inst)
        assert unread_before == 3

        updated = mark_all_notifications_as_read(recipient, inst)
        assert updated == 3

        unread_after = get_unread_notifications_count(recipient, inst)
        assert unread_after == 0

    def test_user_cannot_mark_other_users_notification(self, notifications_setup):
        inst = notifications_setup["inst1"]
        student1 = notifications_setup["student"]
        student2 = notifications_setup["other_student"]

        notif, _ = create_notification(
            institution=inst,
            recipient=student1,
            event_type=NotificationEventType.PLAN_APPROVED,
            subject="Secret Plan",
            preview="Plan info",
        )

        with pytest.raises(Notification.DoesNotExist):
            mark_notification_as_read(notif.id, student2)


@pytest.mark.django_db
class TestNotificationDomainEvents:
    """Verifies domain event helper functions."""

    def test_notify_plan_submitted_and_retry(self, notifications_setup):
        plan = notifications_setup["plan"]
        student = notifications_setup["student"]
        advisor = notifications_setup["advisor"]

        notif, created = notify_plan_submitted(plan, student)
        assert created is True
        assert notif.recipient == advisor
        assert notif.event_type == NotificationEventType.PLAN_SUBMITTED
        assert plan.name in notif.subject

        # Duplicate submission event
        notif_retry, created_retry = notify_plan_submitted(plan, student)
        assert created_retry is False
        assert notif_retry.id == notif.id

    def test_notify_plan_review_decision(self, notifications_setup):
        plan = notifications_setup["plan"]
        student = notifications_setup["student"]
        advisor = notifications_setup["advisor"]

        notif, created = notify_plan_review_decision(plan, "APPROVE", advisor)
        assert created is True
        assert notif.recipient == student
        assert notif.event_type == NotificationEventType.PLAN_APPROVED

    def test_notify_prerequisite_risk_alert(self, notifications_setup):
        inst = notifications_setup["inst1"]
        student = notifications_setup["student"]

        notif, created = notify_prerequisite_risk_alert(
            institution=inst,
            recipient=student,
            course_code="CS301",
            term_code="2026-FALL",
        )
        assert created is True
        assert notif.event_type == NotificationEventType.PREREQUISITE_RISK
        assert "CS301" in notif.subject

        # Same month retry
        _, created_retry = notify_prerequisite_risk_alert(
            institution=inst,
            recipient=student,
            course_code="CS301",
            term_code="2026-FALL",
        )
        assert created_retry is False

    def test_notify_advisor_queue_summary(self, notifications_setup):
        inst = notifications_setup["inst1"]
        advisor = notifications_setup["advisor"]

        notif, created = notify_advisor_queue_summary(
            institution=inst,
            advisor=advisor,
            pending_count=4,
        )
        assert created is True
        assert notif.event_type == NotificationEventType.ADVISOR_QUEUE_SUMMARY
        assert "4" in notif.preview

        # Same day retry
        _, created_retry = notify_advisor_queue_summary(
            institution=inst,
            advisor=advisor,
            pending_count=4,
        )
        assert created_retry is False


@pytest.mark.django_db
class TestNotificationAPIEndpoints:
    """Verifies REST API endpoints with authentication and multi-tenancy."""

    def test_unauthenticated_request_rejected(self):
        client = APIClient()
        resp = client.get("/api/v1/notifications/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_list_notifications_and_unread_filter(self, notifications_setup):
        inst = notifications_setup["inst1"]
        student = notifications_setup["student"]

        # Create 1 unread, 1 read
        notif1, _ = create_notification(
            institution=inst,
            recipient=student,
            event_type=NotificationEventType.PLAN_SUBMITTED,
            subject="Sub 1",
            preview="Preview 1",
            subject_id="sub-1",
        )
        notif2, _ = create_notification(
            institution=inst,
            recipient=student,
            event_type=NotificationEventType.PLAN_APPROVED,
            subject="Sub 2",
            preview="Preview 2",
            subject_id="sub-2",
        )
        mark_notification_as_read(notif2.id, student)

        client = APIClient()
        client.force_authenticate(user=student)

        # All notifications
        resp = client.get("/api/v1/notifications/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) == 2

        # Unread only
        resp_unread = client.get("/api/v1/notifications/?unread_only=true")
        assert resp_unread.status_code == status.HTTP_200_OK
        unread_data = resp_unread.json()
        assert len(unread_data) == 1
        assert unread_data[0]["id"] == str(notif1.id)

    def test_unread_count_endpoint(self, notifications_setup):
        inst = notifications_setup["inst1"]
        student = notifications_setup["student"]

        create_notification(
            institution=inst,
            recipient=student,
            event_type=NotificationEventType.PLAN_SUBMITTED,
            subject="Notice",
            preview="Notice body",
            subject_id="notice-1",
        )

        client = APIClient()
        client.force_authenticate(user=student)

        resp = client.get("/api/v1/notifications/unread-count/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["unread_count"] == 1

    def test_mark_single_read_endpoint(self, notifications_setup):
        inst = notifications_setup["inst1"]
        student = notifications_setup["student"]

        notif, _ = create_notification(
            institution=inst,
            recipient=student,
            event_type=NotificationEventType.PLAN_SUBMITTED,
            subject="Notice",
            preview="Notice body",
        )

        client = APIClient()
        client.force_authenticate(user=student)

        resp = client.post(f"/api/v1/notifications/{notif.id}/read/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["read_status"] == ReadStatus.READ

    def test_mark_single_read_other_user_forbidden(self, notifications_setup):
        inst = notifications_setup["inst1"]
        student = notifications_setup["student"]
        other_student = notifications_setup["other_student"]

        notif, _ = create_notification(
            institution=inst,
            recipient=student,
            event_type=NotificationEventType.PLAN_SUBMITTED,
            subject="Notice",
            preview="Notice body",
        )

        client = APIClient()
        client.force_authenticate(user=other_student)

        resp = client.post(f"/api/v1/notifications/{notif.id}/read/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_all_read_endpoint(self, notifications_setup):
        inst = notifications_setup["inst1"]
        student = notifications_setup["student"]

        for i in range(2):
            create_notification(
                institution=inst,
                recipient=student,
                event_type=NotificationEventType.PLAN_SUBMITTED,
                subject=f"Notice {i}",
                preview=f"Notice body {i}",
                subject_id=f"notif-{i}",
            )

        client = APIClient()
        client.force_authenticate(user=student)

        resp = client.post("/api/v1/notifications/read-all/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["updated_count"] == 2

        # Count endpoint should now return 0
        resp_count = client.get("/api/v1/notifications/unread-count/")
        assert resp_count.json()["unread_count"] == 0

    def test_tenant_isolation(self, notifications_setup):
        inst1 = notifications_setup["inst1"]
        inst2_user = notifications_setup["inst2_user"]

        # Notification created in inst1 for inst2_user (if any error in isolation)
        create_notification(
            institution=inst1,
            recipient=inst2_user,
            event_type=NotificationEventType.PLAN_APPROVED,
            subject="Inst1 Alert",
            preview="Inst1 Preview",
        )

        client = APIClient()
        client.force_authenticate(user=inst2_user)

        # Request with inst2 context should not see inst1 notifications
        resp = client.get("/api/v1/notifications/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 0
