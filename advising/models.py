import uuid

from django.conf import settings
from django.db import models

from common.models import TenantModel


class RiskSeverity(models.TextChoices):
    CRITICAL = "CRITICAL", "Critical Risk"
    WARNING = "WARNING", "Warning / Moderate Risk"
    INFO = "INFO", "Informational"


class RiskCategory(models.TextChoices):
    PREREQUISITE = "PREREQUISITE", "Prerequisite & Eligibility"
    COURSE_OFFERING = "COURSE_OFFERING", "Course Offering & Availability"
    TIMELINE_COMPLETION = "TIMELINE_COMPLETION", "Degree Timeline & Credit Shortfall"
    REGISTRATION = "REGISTRATION", "Registration & Deadlines"
    ACADEMIC_STANDING = "ACADEMIC_STANDING", "Academic Standing & Performance"


class OverallRiskLevel(models.TextChoices):
    LOW = "LOW", "Low Risk"
    MEDIUM = "MEDIUM", "Medium Risk"
    HIGH = "HIGH", "High Risk"
    CRITICAL = "CRITICAL", "Critical Risk"


class AcknowledgmentStatus(models.TextChoices):
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    ACTION_PLAN_CREATED = "ACTION_PLAN_CREATED", "Action Plan Created"
    RESOLVED = "RESOLVED", "Resolved"
    DISMISSED = "DISMISSED", "Dismissed"


class StudentRiskProfile(TenantModel):
    """
    Persisted cache and historical assessment of academic risk indicators for a student.
    Generated deterministically by evaluating transparent academic rules.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_record = models.OneToOneField(
        "academic_records.StudentRecord",
        on_delete=models.CASCADE,
        related_name="risk_profile",
    )
    overall_risk_level = models.CharField(
        max_length=20,
        choices=OverallRiskLevel.choices,
        default=OverallRiskLevel.LOW,
        db_index=True,
    )
    active_risk_count = models.PositiveIntegerField(default=0)
    critical_risk_count = models.PositiveIntegerField(default=0)
    warning_risk_count = models.PositiveIntegerField(default=0)
    info_risk_count = models.PositiveIntegerField(default=0)
    indicators = models.JSONField(
        default=list,
        blank=True,
        help_text="Structured list of evaluated RiskIndicator objects.",
    )
    summary = models.TextField(blank=True, default="")
    assessed_at = models.DateTimeField(auto_now=True, db_index=True)
    last_assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessed_risk_profiles",
    )

    class Meta:
        verbose_name = "Student Risk Profile"
        verbose_name_plural = "Student Risk Profiles"
        ordering = ["-critical_risk_count", "-warning_risk_count", "-assessed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "student_record"],
                name="unique_student_risk_profile_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"RiskProfile({self.student_record.student.username}: {self.overall_risk_level})"

    def clean(self) -> None:
        if self.student_record and self.institution_id != self.student_record.institution_id:
            self.institution = self.student_record.institution
        super().clean()

    def save(self, *args, **kwargs) -> None:
        if self.student_record and not self.institution_id:
            self.institution = self.student_record.institution
        elif self.student_record and self.institution_id != self.student_record.institution_id:
            self.institution = self.student_record.institution
        super().save(*args, **kwargs)


class RiskAcknowledgment(TenantModel):
    """
    Advisor acknowledgment, guidance note, or action plan tied to an identified academic risk.
    Provides an auditable record of advising intervention.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    risk_profile = models.ForeignKey(
        StudentRiskProfile,
        on_delete=models.CASCADE,
        related_name="acknowledgments",
    )
    indicator_code = models.CharField(max_length=64, db_index=True)
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="risk_acknowledgments",
    )
    status = models.CharField(
        max_length=32,
        choices=AcknowledgmentStatus.choices,
        default=AcknowledgmentStatus.ACKNOWLEDGED,
    )
    notes = models.TextField(blank=True, default="")
    action_plan = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Risk Acknowledgment"
        verbose_name_plural = "Risk Acknowledgments"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Acknowledgment({self.indicator_code} by {self.advisor.username}: {self.status})"

    def save(self, *args, **kwargs) -> None:
        if self.risk_profile and not self.institution_id:
            self.institution = self.risk_profile.institution
        super().save(*args, **kwargs)
