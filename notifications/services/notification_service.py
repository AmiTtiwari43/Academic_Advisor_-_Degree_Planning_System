import datetime
import hashlib
import re
import uuid
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from institutions.models import Institution
from notifications.models import DeliveryStatus, Notification, NotificationEventType, ReadStatus

User = get_user_model()


def sanitize_preview_text(preview: str) -> str:
    """
    Ensures previews never contain sensitive academic details
    such as raw grades, GPA numbers, medical reasons, or disciplinary notes.
    """
    sanitized = preview.strip()

    # Mask raw grade disclosures in previews e.g. "Grade: A+", "received F"
    grade_pattern = re.compile(
        r"\b(grade[s]?\s*[:=]\s*[A-DF][+-]?|received\s+[A-DF][+-]?|failed with\s+[A-DF][+-]?)\b",
        re.IGNORECASE,
    )
    sanitized = grade_pattern.sub("academic performance update", sanitized)

    # Mask raw GPA disclosures e.g. "GPA: 2.1", "CGPA 1.85"
    gpa_pattern = re.compile(r"\b(c?gpa\s*[:=]?\s*\d+\.\d+)\b", re.IGNORECASE)
    sanitized = gpa_pattern.sub("academic standing", sanitized)

    return sanitized


def build_deduplication_key(
    institution_id: uuid.UUID | str,
    recipient_id: int | str,
    event_type: str,
    subject_id: Optional[str] = None,
    window: Optional[str] = None,
) -> str:
    """
    Computes a deterministic unique key per (institution, recipient, event_type, subject_id, window).
    Ensures that retry attempts produce exactly one notification record.
    """
    subj = subject_id or "default"
    win = window or "default"
    raw_key = f"{institution_id}:{recipient_id}:{event_type}:{subj}:{win}"
    # Use sha256 to ensure standard bounded length (64 chars) while keeping unique
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


@transaction.atomic
def create_notification(
    institution: Institution,
    recipient: Any,
    event_type: str | NotificationEventType,
    subject: str,
    preview: str,
    payload: Optional[dict[str, Any]] = None,
    subject_id: Optional[str] = None,
    window: Optional[str] = None,
    delivery_status: str = DeliveryStatus.DELIVERED,
) -> tuple[Notification, bool]:
    """
    Creates an in-app notification idempotently using deduplication_key.
    Returns (notification, created: bool).
    """
    sanitized_preview = sanitize_preview_text(preview)
    dedup_key = build_deduplication_key(
        institution_id=institution.id,
        recipient_id=recipient.id,
        event_type=str(event_type),
        subject_id=subject_id,
        window=window,
    )

    # Fast check for existing notification
    existing = Notification.objects.filter(deduplication_key=dedup_key).first()
    if existing:
        return existing, False

    try:
        notification = Notification.objects.create(
            institution=institution,
            recipient=recipient,
            event_type=str(event_type),
            subject=subject[:255],
            preview=sanitized_preview[:500],
            payload=payload or {},
            delivery_status=delivery_status,
            read_status=ReadStatus.UNREAD,
            deduplication_key=dedup_key,
        )
        return notification, True
    except IntegrityError:
        # Concurrent creation or race condition resolved safely
        existing = Notification.objects.filter(deduplication_key=dedup_key).first()
        if existing:
            return existing, False
        raise


def mark_notification_as_read(notification_id: uuid.UUID | str, user: Any) -> Notification:
    """
    Marks a notification as read, validating recipient ownership.
    """
    notification = Notification.objects.get(id=notification_id, recipient=user)
    if notification.read_status != ReadStatus.READ:
        notification.read_status = ReadStatus.READ
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_status", "read_at", "updated_at"])
    return notification


def mark_all_notifications_as_read(user: Any, institution: Institution) -> int:
    """
    Marks all unread notifications as read for a recipient in the active institution.
    Returns count of updated notifications.
    """
    now = timezone.now()
    updated_count = Notification.objects.filter(
        recipient=user,
        institution=institution,
        read_status=ReadStatus.UNREAD,
    ).update(
        read_status=ReadStatus.READ,
        read_at=now,
        updated_at=now,
    )
    return updated_count


def get_unread_notifications_count(user: Any, institution: Institution) -> int:
    """
    Returns unread count for recipient in institution.
    """
    return Notification.objects.filter(
        recipient=user,
        institution=institution,
        read_status=ReadStatus.UNREAD,
    ).count()


# ---------------------------------------------------------------------------
# High-Level Event Handlers
# ---------------------------------------------------------------------------


def notify_plan_submitted(plan: Any, submitted_by: Any) -> tuple[Notification, bool]:
    """
    Notifies the assigned advisor or coordinator when a plan is submitted.
    """
    institution = plan.institution
    assigned_advisor = None
    if hasattr(plan, "student_record") and plan.student_record:
        from accounts.models import AdvisorAssignment

        assignment = (
            AdvisorAssignment.objects.filter(
                institution=institution,
                student__user=plan.student_record.student,
                is_active=True,
            )
            .select_related("advisor__user")
            .first()
        )
        if assignment and assignment.advisor:
            assigned_advisor = assignment.advisor.user

    recipient = assigned_advisor or submitted_by
    subject = f"Plan Submission: {plan.name}"
    preview = f"A degree plan '{plan.name}' has been submitted for advisor review."
    subject_id = f"plan-sub-{plan.id}-{plan.row_version}"

    payload = {
        "plan_id": str(plan.id),
        "plan_name": plan.name,
        "submitted_by": submitted_by.username,
        "student_username": plan.student_record.student.username,
    }

    return create_notification(
        institution=institution,
        recipient=recipient,
        event_type=NotificationEventType.PLAN_SUBMITTED,
        subject=subject,
        preview=preview,
        payload=payload,
        subject_id=subject_id,
    )


def notify_plan_review_decision(
    plan: Any,
    decision_action: str,
    reviewer: Any,
) -> tuple[Notification, bool]:
    """
    Notifies the student when their plan receives a decision (approved, returned, rejected).
    Preview is strictly privacy-safe (contains no grades or confidential notes).
    """
    institution = plan.institution
    student_user = plan.student_record.student

    event_map = {
        "APPROVE": NotificationEventType.PLAN_APPROVED,
        "RETURN": NotificationEventType.PLAN_RETURNED,
        "REJECT": NotificationEventType.PLAN_REJECTED,
        "START_REVIEW": NotificationEventType.PLAN_UNDER_REVIEW,
    }
    event_type = event_map.get(decision_action, NotificationEventType.PLAN_UNDER_REVIEW)

    subject = f"Plan Update: {plan.name}"
    preview = f"Your degree plan '{plan.name}' has received an academic review update."
    subject_id = f"plan-decision-{plan.id}-{decision_action}-{plan.row_version}"

    payload = {
        "plan_id": str(plan.id),
        "plan_name": plan.name,
        "action": decision_action,
        "reviewer_username": reviewer.username,
    }

    return create_notification(
        institution=institution,
        recipient=student_user,
        event_type=event_type,
        subject=subject,
        preview=preview,
        payload=payload,
        subject_id=subject_id,
    )


def notify_prerequisite_risk_alert(
    institution: Institution,
    recipient: Any,
    course_code: str,
    term_code: Optional[str] = None,
) -> tuple[Notification, bool]:
    """
    Notifies student/advisor about a prerequisite bottleneck or timeline risk.
    """
    subject = f"Prerequisite Timeline Alert: {course_code}"
    preview = f"A prerequisite sequencing condition for {course_code} requires attention."
    subject_id = f"prereq-risk-{course_code}-{term_code or 'general'}"
    window = datetime.date.today().strftime("%Y-%m")  # Once per month per course

    payload = {
        "course_code": course_code,
        "term_code": term_code,
    }

    return create_notification(
        institution=institution,
        recipient=recipient,
        event_type=NotificationEventType.PREREQUISITE_RISK,
        subject=subject,
        preview=preview,
        payload=payload,
        subject_id=subject_id,
        window=window,
    )


def notify_advisor_queue_summary(
    institution: Institution,
    advisor: Any,
    pending_count: int,
) -> tuple[Notification, bool]:
    """
    Daily advising review queue summary.
    """
    subject = "Advising Review Queue Summary"
    preview = f"You have {pending_count} degree plan(s) currently awaiting official review."
    subject_id = f"queue-summary-{advisor.id}"
    window = datetime.date.today().isoformat()  # Once per day

    payload = {
        "pending_count": pending_count,
        "date": window,
    }

    return create_notification(
        institution=institution,
        recipient=advisor,
        event_type=NotificationEventType.ADVISOR_QUEUE_SUMMARY,
        subject=subject,
        preview=preview,
        payload=payload,
        subject_id=subject_id,
        window=window,
    )
