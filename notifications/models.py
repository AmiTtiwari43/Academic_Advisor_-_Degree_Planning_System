import uuid

from django.contrib.auth import get_user_model
from django.db import models

from institutions.models import Institution

User = get_user_model()


class NotificationEventType(models.TextChoices):
    PLAN_SUBMITTED = "PLAN_SUBMITTED", "Plan Submitted"
    PLAN_UNDER_REVIEW = "PLAN_UNDER_REVIEW", "Plan Under Review"
    PLAN_APPROVED = "PLAN_APPROVED", "Plan Approved"
    PLAN_RETURNED = "PLAN_RETURNED", "Plan Returned for Revision"
    PLAN_REJECTED = "PLAN_REJECTED", "Plan Rejected"
    REGISTRATION_REMINDER = "REGISTRATION_REMINDER", "Registration Reminder"
    PREREQUISITE_RISK = "PREREQUISITE_RISK", "Prerequisite Risk Alert"
    ADVISOR_QUEUE_SUMMARY = "ADVISOR_QUEUE_SUMMARY", "Advisor Queue Summary"


class DeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    DELIVERED = "DELIVERED", "Delivered"
    FAILED = "FAILED", "Failed"


class ReadStatus(models.TextChoices):
    UNREAD = "UNREAD", "Unread"
    READ = "READ", "Read"


class Notification(models.Model):
    """
    In-app notification model with delivery status, read status,
    and unique deduplication key for retry idempotency.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    event_type = models.CharField(
        max_length=64,
        choices=NotificationEventType.choices,
        db_index=True,
    )
    subject = models.CharField(max_length=255)
    preview = models.CharField(max_length=500)
    payload = models.JSONField(default=dict, blank=True)
    delivery_status = models.CharField(
        max_length=32,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.DELIVERED,
    )
    read_status = models.CharField(
        max_length=32,
        choices=ReadStatus.choices,
        default=ReadStatus.UNREAD,
        db_index=True,
    )
    read_at = models.DateTimeField(null=True, blank=True)
    deduplication_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Deterministic key ensuring retry attempts produce exactly one notification record.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read_status", "-created_at"]),
            models.Index(fields=["institution", "recipient", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Notification({self.event_type}, to={self.recipient.username}, read={self.read_status})"
