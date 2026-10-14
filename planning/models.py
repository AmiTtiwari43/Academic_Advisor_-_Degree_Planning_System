import uuid
from typing import Any

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from academic_records.models import AcademicTerm, StudentRecord
from curriculum.models import Course, CurriculumVersion
from institutions.models import Institution


class PlanVersionImmutabilityError(ValidationError):
    """Raised when an attempt is made to mutate or delete a frozen PlanVersion snapshot."""
    pass


class PlanStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    ARCHIVED = "ARCHIVED", "Archived"


class PlanVersionStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    RETURNED = "RETURNED", "Returned"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class Plan(models.Model):
    """
    Multi-semester graduation plan owned by a student.
    Plans are simulated independently and never modify official academic records.
    Uses optimistic concurrency control via `row_version`.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="plans", db_index=True
    )
    student_record = models.ForeignKey(
        StudentRecord, on_delete=models.CASCADE, related_name="plans", db_index=True
    )
    curriculum_version = models.ForeignKey(
        CurriculumVersion, on_delete=models.PROTECT, related_name="plans"
    )
    name = models.CharField(max_length=120, default="Primary Academic Plan")
    is_primary = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20, choices=PlanStatus.choices, default=PlanStatus.DRAFT
    )
    row_version = models.PositiveIntegerField(
        default=1,
        help_text="Incremented on every update for optimistic concurrency protection.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-updated_at"]
        verbose_name = "Degree Plan"
        verbose_name_plural = "Degree Plans"

    def __str__(self) -> str:
        return f"{self.name} - {self.student_record.student.username} (v{self.row_version})"

    def clean(self) -> None:
        super().clean()
        if self.curriculum_version_id and self.institution_id:
            if self.curriculum_version.institution_id != self.institution_id:
                raise ValidationError("Curriculum version must belong to the plan's institution.")
        if self.student_record_id and self.institution_id:
            if self.student_record.institution_id != self.institution_id:
                raise ValidationError("Student record must belong to the plan's institution.")


class PlanItem(models.Model):
    """
    A specific course planned for a future academic term within a degree plan.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="plan_items"
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="items", db_index=True
    )
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="plan_items"
    )
    planned_term = models.ForeignKey(
        AcademicTerm, on_delete=models.PROTECT, related_name="plan_items"
    )
    term_index = models.PositiveSmallIntegerField(
        help_text="1-indexed sequence number of the planned semester (e.g. 1, 2, 3...)"
    )
    position = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display/ordering position of the course within this planned term.",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["term_index", "position", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "course"],
                name="unique_course_per_plan",
            ),
        ]
        verbose_name = "Plan Item"
        verbose_name_plural = "Plan Items"

    def __str__(self) -> str:
        return f"{self.course.code} in Term {self.term_index} ({self.planned_term.code})"

    def clean(self) -> None:
        super().clean()
        if self.plan_id and self.institution_id:
            if self.plan.institution_id != self.institution_id:
                raise ValidationError("Plan item institution must match plan institution.")
        if self.planned_term_id and self.institution_id:
            if self.planned_term.institution_id != self.institution_id:
                raise ValidationError("Planned term must belong to the same institution.")


class PlanVersion(models.Model):
    """
    Immutable frozen snapshot of a plan submitted for advisor review.
    Snapshot data contains complete frozen schedule, course selections, and simulation state.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="plan_versions"
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="versions", db_index=True
    )
    version_number = models.PositiveIntegerField()
    snapshot_data = models.JSONField(
        help_text="Frozen JSON structure of items, audit status, and simulation verdict."
    )
    status = models.CharField(
        max_length=20,
        choices=PlanVersionStatus.choices,
        default=PlanVersionStatus.SUBMITTED,
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="submitted_plan_versions"
    )
    submission_note = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "version_number"],
                name="unique_version_number_per_plan",
            ),
        ]
        verbose_name = "Plan Version Snapshot"
        verbose_name_plural = "Plan Version Snapshots"

    def __str__(self) -> str:
        return f"{self.plan.name} - Version {self.version_number} ({self.status})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Immutability Guard: If updating an existing version, snapshot_data cannot change
        if self.pk:
            existing = PlanVersion.objects.filter(pk=self.pk).first()
            if existing:
                if existing.snapshot_data != self.snapshot_data:
                    raise PlanVersionImmutabilityError(
                        "PlanVersion snapshot_data is immutable once submitted."
                    )
                if existing.version_number != self.version_number:
                    raise PlanVersionImmutabilityError(
                        "PlanVersion version_number cannot be modified."
                    )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise PlanVersionImmutabilityError(
            "Submitted plan version snapshots are immutable and cannot be deleted."
        )
