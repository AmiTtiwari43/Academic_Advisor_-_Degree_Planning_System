import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TenantModel
from rule_engine.core import RuleValidationError, validate_rule_strict


class CurriculumImmutabilityError(ValidationError):
    """Raised when an attempt is made to mutate a published or archived curriculum version or child."""


class DegreeType(models.TextChoices):
    BACHELOR = "BACHELOR", "Bachelor of Science / Arts"
    MASTER = "MASTER", "Master of Science / Arts"
    DOCTORATE = "DOCTORATE", "Doctor of Philosophy"
    ASSOCIATE = "ASSOCIATE", "Associate Degree"
    CERTIFICATE = "CERTIFICATE", "Academic Certificate"


class CurriculumStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED = "ARCHIVED", "Archived"


class RequirementGroupType(models.TextChoices):
    MANDATORY = "MANDATORY", "Mandatory Core"
    ELECTIVE = "ELECTIVE", "Elective Group"
    CREDIT_CATEGORY = "CREDIT_CATEGORY", "Credit Category Threshold"


class DeliveryMode(models.TextChoices):
    IN_PERSON = "IN_PERSON", "In-Person"
    ONLINE = "ONLINE", "Online"
    HYBRID = "HYBRID", "Hybrid"


class Programme(TenantModel):
    """
    Academic degree programme offered by an institution (e.g. BS Computer Science).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=255)
    degree_type = models.CharField(
        max_length=32, choices=DegreeType.choices, default=DegreeType.BACHELOR
    )
    department = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_programme_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class CurriculumVersion(TenantModel):
    """
    Versioned curriculum definition for a degree programme.
    Drafts can be mutated; published versions are strictly immutable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    programme = models.ForeignKey(
        Programme,
        on_delete=models.CASCADE,
        related_name="curriculum_versions",
    )
    version_number = models.PositiveIntegerField()
    academic_year = models.CharField(max_length=32)
    status = models.CharField(
        max_length=32,
        choices=CurriculumStatus.choices,
        default=CurriculumStatus.DRAFT,
        db_index=True,
    )
    total_credits_required = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("120.00")
    )
    min_cgpa_required = models.DecimalField(
        max_digits=4, decimal_places=3, default=Decimal("2.000")
    )
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="published_curricula",
    )
    change_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["programme", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["programme", "version_number"],
                name="unique_version_per_programme",
            ),
            models.CheckConstraint(
                condition=models.Q(total_credits_required__gte=0),
                name="check_version_positive_credits",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.programme.code} v{self.version_number} ({self.status})"

    @property
    def is_editable(self) -> bool:
        return self.status == CurriculumStatus.DRAFT

    def save(self, *args, **kwargs):
        if self.pk:
            old = CurriculumVersion.objects.filter(pk=self.pk).first()
            if old:
                if old.status == CurriculumStatus.PUBLISHED:
                    # Only state transition allowed is PUBLISHED -> ARCHIVED
                    if self.status == CurriculumStatus.ARCHIVED:
                        # Allow archiving without changing structural fields
                        if (
                            self.version_number != old.version_number
                            or self.programme_id != old.programme_id
                            or self.total_credits_required != old.total_credits_required
                            or self.min_cgpa_required != old.min_cgpa_required
                        ):
                            raise CurriculumImmutabilityError(
                                "Cannot modify structural fields of a published curriculum version."
                            )
                    else:
                        raise CurriculumImmutabilityError(
                            "Published curriculum versions are immutable and cannot be updated."
                        )
                elif old.status == CurriculumStatus.ARCHIVED:
                    raise CurriculumImmutabilityError(
                        "Archived curriculum versions are immutable and cannot be modified."
                    )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status in (CurriculumStatus.PUBLISHED, CurriculumStatus.ARCHIVED):
            raise CurriculumImmutabilityError(
                "Published or archived curriculum versions are immutable and cannot be deleted."
            )
        return super().delete(*args, **kwargs)


class CreditCategory(TenantModel):
    """
    Taxonomy for categorizing coursework and requirements (e.g. CORE, ELECTIVE, GEN_ED).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_credit_category_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Course(TenantModel):
    """
    Catalog course record belonging to an institution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    credits = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("3.00"))
    default_credit_category = models.ForeignKey(
        CreditCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="courses",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_course_code_per_institution",
            ),
            models.CheckConstraint(
                condition=models.Q(credits__gte=0),
                name="check_course_positive_credits",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.title} ({self.credits} cr)"


class RequirementGroup(TenantModel):
    """
    Hierarchical grouping of graduation requirements (e.g., General Ed, Major Core, Capstone).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    curriculum_version = models.ForeignKey(
        CurriculumVersion,
        on_delete=models.CASCADE,
        related_name="requirement_groups",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    group_type = models.CharField(
        max_length=32,
        choices=RequirementGroupType.choices,
        default=RequirementGroupType.MANDATORY,
    )
    min_credits = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    min_courses = models.PositiveIntegerField(default=0)
    min_cgpa = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    credit_category = models.ForeignKey(
        CreditCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requirement_groups",
    )
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    courses = models.ManyToManyField(
        Course,
        through="RequirementGroupCourse",
        related_name="requirement_groups",
        blank=True,
    )

    class Meta:
        ordering = ["curriculum_version", "display_order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(min_credits__gte=0),
                name="check_req_group_positive_credits",
            )
        ]

    def __str__(self) -> str:
        return f"{self.curriculum_version.programme.code} - {self.name}"

    def clean(self):
        super().clean()
        if (
            self.curriculum_version_id
            and self.curriculum_version.status == CurriculumStatus.PUBLISHED
        ):
            raise CurriculumImmutabilityError(
                "Cannot modify requirement groups of a published curriculum version."
            )
        # Prevent self-parenting
        if self.parent_id and self.pk and self.parent_id == self.pk:
            raise ValidationError("A requirement group cannot be its own parent.")
        # Ensure parent belongs to same curriculum version
        if self.parent_id and self.parent.curriculum_version_id != self.curriculum_version_id:
            raise ValidationError("Parent group must belong to the same curriculum version.")

    def save(self, *args, **kwargs):
        if (
            self.curriculum_version_id
            and self.curriculum_version.status == CurriculumStatus.PUBLISHED
        ):
            raise CurriculumImmutabilityError(
                "Cannot modify requirement groups of a published curriculum version."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.curriculum_version.status == CurriculumStatus.PUBLISHED:
            raise CurriculumImmutabilityError(
                "Cannot delete requirement groups of a published curriculum version."
            )
        return super().delete(*args, **kwargs)


class RequirementGroupCourse(models.Model):
    """
    Associates a catalog course to a requirement group within a curriculum version.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requirement_group = models.ForeignKey(
        RequirementGroup,
        on_delete=models.CASCADE,
        related_name="group_courses",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    is_mandatory = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["requirement_group", "display_order", "course__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["requirement_group", "course"],
                name="unique_course_per_group",
            )
        ]

    def __str__(self) -> str:
        return f"{self.requirement_group.name} -> {self.course.code}"

    def clean(self):
        super().clean()
        if self.requirement_group.curriculum_version.status == CurriculumStatus.PUBLISHED:
            raise CurriculumImmutabilityError(
                "Cannot modify course associations of a published curriculum version."
            )

    def save(self, *args, **kwargs):
        if self.requirement_group.curriculum_version.status == CurriculumStatus.PUBLISHED:
            raise CurriculumImmutabilityError(
                "Cannot modify course associations of a published curriculum version."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.requirement_group.curriculum_version.status == CurriculumStatus.PUBLISHED:
            raise CurriculumImmutabilityError(
                "Cannot delete course associations of a published curriculum version."
            )
        return super().delete(*args, **kwargs)


class PrerequisiteRule(TenantModel):
    """
    Prerequisite and corequisite rules assigned to a course in a specific curriculum version.
    Stores structured JSON validated by Phase 03 ASTValidator.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    curriculum_version = models.ForeignKey(
        CurriculumVersion,
        on_delete=models.CASCADE,
        related_name="prerequisite_rules",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="prerequisite_rules",
    )
    rule_json = models.JSONField(default=dict)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["curriculum_version", "course__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["curriculum_version", "course"],
                name="unique_rule_per_version_course",
            )
        ]

    def __str__(self) -> str:
        return f"Rule: {self.course.code} ({self.curriculum_version})"

    def clean(self):
        super().clean()
        if self.curriculum_version.status == CurriculumStatus.PUBLISHED:
            raise CurriculumImmutabilityError(
                "Cannot modify prerequisite rules of a published curriculum version."
            )
        # Validate AST strictly
        try:
            validate_rule_strict(self.rule_json)
        except (RuleValidationError, ValueError) as exc:
            raise ValidationError(f"Invalid prerequisite rule AST: {exc}") from exc

    def save(self, *args, **kwargs):
        if self.curriculum_version.status == CurriculumStatus.PUBLISHED:
            raise CurriculumImmutabilityError(
                "Cannot modify prerequisite rules of a published curriculum version."
            )
        try:
            validate_rule_strict(self.rule_json)
        except (RuleValidationError, ValueError) as exc:
            raise ValidationError(f"Invalid prerequisite rule AST: {exc}") from exc
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.curriculum_version.status == CurriculumStatus.PUBLISHED:
            raise CurriculumImmutabilityError(
                "Cannot delete prerequisite rules of a published curriculum version."
            )
        return super().delete(*args, **kwargs)


class CourseOffering(TenantModel):
    """
    Term availability schedule for a course (e.g. Fall 2026, 45 capacity, In-Person).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="offerings",
    )
    academic_term = models.CharField(max_length=32)
    academic_year = models.CharField(max_length=32)
    is_offered = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(default=30)
    delivery_mode = models.CharField(
        max_length=32,
        choices=DeliveryMode.choices,
        default=DeliveryMode.IN_PERSON,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["academic_year", "academic_term", "course__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "academic_term", "academic_year"],
                name="unique_offering_per_course_term_year",
            )
        ]

    def __str__(self) -> str:
        return f"{self.course.code} - {self.academic_term} ({self.delivery_mode})"


class StudentCurriculumAssignment(TenantModel):
    """
    Pins a student to an authoritative published curriculum version for a degree programme.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="curriculum_assignments",
    )
    curriculum_version = models.ForeignKey(
        CurriculumVersion,
        on_delete=models.CASCADE,
        related_name="student_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="curriculum_assignments_given",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-assigned_at"]

    def __str__(self) -> str:
        return f"{self.student.username} -> {self.curriculum_version}"

    def clean(self):
        super().clean()
        if self.curriculum_version.status != CurriculumStatus.PUBLISHED:
            raise ValidationError("Students can only be assigned to published curriculum versions.")
        # Ensure student and curriculum version belong to the exact same institution
        if self.institution_id != self.curriculum_version.institution_id:
            raise ValidationError(
                "Curriculum version belongs to a different institution than assignment."
            )
        # Ensure student has membership in the institution
        if not self.student.institution_memberships.filter(
            institution_id=self.institution_id, is_active=True
        ).exists():
            raise ValidationError("Student is not an active member of the specified institution.")

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.is_active:
            # Deactivate any previous active assignment for the same student and programme
            StudentCurriculumAssignment.objects.filter(
                student=self.student,
                curriculum_version__programme=self.curriculum_version.programme,
                is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
