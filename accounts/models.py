import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TenantModel


class Role(models.TextChoices):
    STUDENT = "STUDENT", "Student"
    ADVISOR = "ADVISOR", "Faculty advisor"
    COORDINATOR = "COORDINATOR", "Programme coordinator"
    HOD = "HOD", "Head of Department"
    ADMIN = "ADMIN", "System administrator"
    MENTOR = "MENTOR", "Mentor"
    MODERATOR = "MODERATOR", "Moderator"


class UserProfile(models.Model):
    """
    User profile extension for global user metadata.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone_number = models.CharField(max_length=32, blank=True, default="")
    preferred_name = models.CharField(max_length=128, blank=True, default="")
    registration_number = models.CharField(max_length=64, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_or_generate_registration_number(self) -> str:
        if self.registration_number:
            return self.registration_number
        mem = self.user.institution_memberships.filter(is_active=True).first() if self.user_id else None
        role = mem.role if mem else ""
        if role in [Role.STUDENT]:
            prefix = "STU"
        elif role in [Role.ADVISOR, Role.MENTOR, "FACULTY"]:
            prefix = "FAC"
        else:
            prefix = "ADM"
        uid = self.user_id or 1
        reg = f"{prefix}-2026-{uid:04d}"
        self.registration_number = reg
        self.save(update_fields=["registration_number"])
        return reg

    def save(self, *args, **kwargs):
        if not self.registration_number and self.user_id:
            try:
                mem = self.user.institution_memberships.filter(is_active=True).first()
                role = mem.role if mem else ""
            except Exception:
                role = ""
            if role in [Role.STUDENT]:
                prefix = "STU"
            elif role in [Role.ADVISOR, Role.MENTOR, "FACULTY"]:
                prefix = "FAC"
            else:
                prefix = "ADM"
            self.registration_number = f"{prefix}-2026-{self.user_id:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        reg = f" ({self.registration_number})" if self.registration_number else ""
        return f"Profile of {self.user.username}{reg}"


class InstitutionMembership(TenantModel):
    """
    Associates a user with an institution and specific institutional role.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="institution_memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["institution", "user", "role"]
        unique_together = [("user", "institution", "role")]

    def __str__(self):
        return f"{self.user.username} - {self.institution.code} ({self.role})"


class AdvisorAssignment(TenantModel):
    """
    Active or historical academic advising relationship between a faculty advisor
    and a student within an institution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    advisor = models.ForeignKey(
        InstitutionMembership,
        on_delete=models.CASCADE,
        related_name="advising_assignments",
    )
    student = models.ForeignKey(
        InstitutionMembership,
        on_delete=models.CASCADE,
        related_name="advisor_assignments",
    )
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-assigned_at"]

    def clean(self):
        super().clean()
        if self.advisor_id and self.student_id:
            if self.advisor.institution_id != self.institution_id:
                raise ValidationError("Advisor must belong to the assigned institution.")
            if self.student.institution_id != self.institution_id:
                raise ValidationError("Student must belong to the assigned institution.")
            if self.advisor.role != Role.ADVISOR:
                raise ValidationError("Assigned advisor must possess the ADVISOR role.")
            if self.student.role != Role.STUDENT:
                raise ValidationError("Assigned student must possess the STUDENT role.")
            if self.advisor.user_id == self.student.user_id:
                raise ValidationError("A user cannot be assigned as advisor to themselves.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Advisor {self.advisor.user.username} -> Student {self.student.user.username} ({self.institution.code})"
