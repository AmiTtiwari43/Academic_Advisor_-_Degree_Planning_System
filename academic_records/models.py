from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TenantModel


class TermSeason(models.TextChoices):
    FALL = "FALL", "Fall"
    SPRING = "SPRING", "Spring"
    SUMMER = "SUMMER", "Summer"
    WINTER = "WINTER", "Winter"


class AcademicTerm(TenantModel):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    season = models.CharField(max_length=20, choices=TermSeason.choices)
    year = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "academic_terms"
        ordering = ["year", "start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_academic_term_code_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    def clean(self) -> None:
        super().clean()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError(
                {"end_date": "Term end date must be strictly after start date."}
            )


class RepeatedCoursePolicy(models.TextChoices):
    BEST_GRADE = "BEST_GRADE", "Best Grade"
    LATEST_GRADE = "LATEST_GRADE", "Latest Grade"
    ALL_ATTEMPTS = "ALL_ATTEMPTS", "All Attempts Counted"


class StudentRecordStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    PROBATION = "PROBATION", "Academic Probation"
    SUSPENDED = "SUSPENDED", "Suspended"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    GRADUATED = "GRADUATED", "Graduated"


class StudentRecord(TenantModel):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="academic_records",
    )
    programme = models.ForeignKey(
        "curriculum.Programme",
        on_delete=models.PROTECT,
        related_name="student_records",
    )
    pinned_curriculum = models.ForeignKey(
        "curriculum.CurriculumVersion",
        on_delete=models.PROTECT,
        related_name="assigned_student_records",
    )
    enrollment_term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.PROTECT,
        related_name="+",
    )
    expected_graduation_term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    repeated_course_policy = models.CharField(
        max_length=30,
        choices=RepeatedCoursePolicy.choices,
        default=RepeatedCoursePolicy.BEST_GRADE,
    )
    status = models.CharField(
        max_length=20,
        choices=StudentRecordStatus.choices,
        default=StudentRecordStatus.ACTIVE,
    )
    cached_cgpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    cached_total_credits = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_academic_records"
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "student"],
                name="unique_student_record_per_institution",
            ),
        ]

    def __str__(self) -> str:
        return f"Student {self.student_id} ({self.programme.code})"

    def clean(self) -> None:
        super().clean()
        if (
            self.pinned_curriculum_id
            and self.pinned_curriculum.institution_id != self.institution_id
        ):
            raise ValidationError(
                {"pinned_curriculum": "Pinned curriculum must belong to the student's institution."}
            )
        if (
            self.pinned_curriculum_id
            and self.programme_id
            and self.pinned_curriculum.programme_id != self.programme_id
        ):
            raise ValidationError(
                {"pinned_curriculum": "Pinned curriculum must belong to the student's degree programme."}
            )
        if (
            self.pinned_curriculum_id
            and self.pinned_curriculum.status != "PUBLISHED"
        ):
            raise ValidationError(
                {"pinned_curriculum": "Cannot pin a student to a draft or archived curriculum version."}
            )


class TranscriptEntryStatus(models.TextChoices):
    COMPLETED = "COMPLETED", "Completed"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    FAILED = "FAILED", "Failed"


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "UNVERIFIED", "Unverified"
    VERIFIED = "VERIFIED", "Verified"
    OFFICIAL_SEALED = "OFFICIAL_SEALED", "Official Sealed"


class TranscriptEntry(TenantModel):
    student_record = models.ForeignKey(
        StudentRecord,
        on_delete=models.CASCADE,
        related_name="transcript_entries",
    )
    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.PROTECT,
        related_name="transcript_entries",
    )
    term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.PROTECT,
        related_name="transcript_entries",
    )
    grade = models.CharField(max_length=5, blank=True, default="")
    credits_attempted = models.DecimalField(max_digits=5, decimal_places=2)
    credits_earned = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=20,
        choices=TranscriptEntryStatus.choices,
        default=TranscriptEntryStatus.COMPLETED,
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.VERIFIED,
    )
    attempt_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transcript_entries"
        ordering = ["term__year", "term__start_date", "course__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["student_record", "course", "term", "attempt_number"],
                name="unique_transcript_attempt_per_term",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_record.student_id} - {self.course.code} ({self.term.code}): {self.grade}"

    def clean(self) -> None:
        super().clean()
        if self.course_id and self.course.institution_id != self.institution_id:
            raise ValidationError({"course": "Course must belong to the same institution."})
        if self.term_id and self.term.institution_id != self.institution_id:
            raise ValidationError({"term": "Academic term must belong to the same institution."})
        if self.student_record_id and self.student_record.institution_id != self.institution_id:
            raise ValidationError({"student_record": "Student record must belong to the same institution."})


class TransferCredit(TenantModel):
    student_record = models.ForeignKey(
        StudentRecord,
        on_delete=models.CASCADE,
        related_name="transfer_credits",
    )
    course_code = models.CharField(max_length=30)
    course_title = models.CharField(max_length=200, blank=True, default="")
    source_institution = models.CharField(max_length=200)
    credits = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5, blank=True, default="CR")
    is_verified = models.BooleanField(default=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transfer_credits"
        ordering = ["course_code"]

    def __str__(self) -> str:
        return f"Transfer {self.course_code} ({self.credits} cr) from {self.source_institution}"


class Exemption(TenantModel):
    student_record = models.ForeignKey(
        StudentRecord,
        on_delete=models.CASCADE,
        related_name="exemptions",
    )
    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.PROTECT,
        related_name="exemptions",
    )
    reason = models.TextField()
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "course_exemptions"
        constraints = [
            models.UniqueConstraint(
                fields=["student_record", "course"],
                name="unique_exemption_per_student_course",
            ),
        ]

    def __str__(self) -> str:
        return f"Exemption: {self.student_record.student_id} - {self.course.code}"
