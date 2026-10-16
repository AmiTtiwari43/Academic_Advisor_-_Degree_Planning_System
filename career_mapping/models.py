"""
Career Objective and Skill Mapping Models (Prompt 08D).
Enables institutional skill taxonomies, course-to-skill mappings,
career objective pathways, and student career preferences.
"""

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from common.models import TenantModel


class SkillCategory(models.TextChoices):
    TECHNICAL = "TECHNICAL", "Technical"
    ANALYTICAL = "ANALYTICAL", "Analytical"
    DOMAIN = "DOMAIN", "Domain Knowledge"
    SOFT = "SOFT", "Soft Skills"
    TOOL = "TOOL", "Tools & Frameworks"


class ProficiencyLevel(models.TextChoices):
    INTRODUCTORY = "INTRODUCTORY", "Introductory"
    INTERMEDIATE = "INTERMEDIATE", "Intermediate"
    ADVANCED = "ADVANCED", "Advanced"
    MASTERY = "MASTERY", "Mastery"


PROFICIENCY_SCORES = {
    ProficiencyLevel.INTRODUCTORY: 1,
    ProficiencyLevel.INTERMEDIATE: 2,
    ProficiencyLevel.ADVANCED: 3,
    ProficiencyLevel.MASTERY: 4,
}


class Skill(TenantModel):
    """
    Standardized competency or technical capability catalogued by an institution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=128)
    category = models.CharField(
        max_length=32,
        choices=SkillCategory.choices,
        default=SkillCategory.TECHNICAL,
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "career_skills"
        ordering = ["category", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_skill_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def clean(self) -> None:
        super().clean()
        self.code = self.code.strip().upper()


class CareerObjective(TenantModel):
    """
    Professional role, specialization, or career outcome defined by the institution.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    programme = models.ForeignKey(
        "curriculum.Programme",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="career_objectives",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "career_objectives"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                name="unique_career_objective_code_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.code})"

    def clean(self) -> None:
        super().clean()
        self.code = self.code.strip().upper()
        if self.programme is not None and self.programme.institution_id != self.institution_id:
            raise ValidationError(
                {"programme": "Programme must belong to the same institution as the career objective."}
            )



class CareerSkillRequirement(models.Model):
    """
    Specifies a required or recommended skill for achieving a career objective.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    career_objective = models.ForeignKey(
        CareerObjective,
        on_delete=models.CASCADE,
        related_name="skill_requirements",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="career_requirements",
    )
    min_proficiency = models.CharField(
        max_length=32,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.INTERMEDIATE,
    )
    is_critical = models.BooleanField(
        default=True,
        help_text="Critical skills are core requirements; non-critical are recommended electives.",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "career_skill_requirements"
        ordering = ["-is_critical", "display_order", "skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["career_objective", "skill"],
                name="unique_skill_per_career_objective",
            )
        ]

    def __str__(self) -> str:
        crit_str = "Critical" if self.is_critical else "Recommended"
        return f"{self.career_objective.title} -> {self.skill.name} ({crit_str}, min {self.min_proficiency})"

    def clean(self) -> None:
        super().clean()
        if (
            self.career_objective_id
            and self.skill_id
            and self.career_objective.institution_id != self.skill.institution_id
        ):
            raise ValidationError(
                {"skill": "Skill must belong to the same institution as the career objective."}
            )


class CourseSkillMapping(TenantModel):
    """
    Maps an academic course to the skill competencies and proficiency depth it delivers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="skill_mappings",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="course_mappings",
    )
    proficiency_level = models.CharField(
        max_length=32,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.INTERMEDIATE,
    )
    coverage_weight = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("1.00"),
        help_text="Proportional depth or instructional focus (0.1 to 1.0).",
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "course_skill_mappings"
        ordering = ["course__code", "skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "skill"],
                name="unique_skill_per_course",
            ),
            models.CheckConstraint(
                condition=models.Q(coverage_weight__gt=0) & models.Q(coverage_weight__lte=1.00),
                name="check_course_skill_coverage_weight_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course.code} delivers {self.skill.name} ({self.proficiency_level})"

    def clean(self) -> None:
        super().clean()
        if (
            self.course_id
            and self.skill_id
            and self.course.institution_id != self.skill.institution_id
        ):
            raise ValidationError(
                {"skill": "Skill must belong to the same institution as the course."}
            )


class StudentCareerPreference(TenantModel):
    """
    A student's declared career goal(s), ranked by priority.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_record = models.ForeignKey(
        "academic_records.StudentRecord",
        on_delete=models.CASCADE,
        related_name="career_preferences",
    )
    career_objective = models.ForeignKey(
        CareerObjective,
        on_delete=models.CASCADE,
        related_name="student_preferences",
    )
    priority = models.PositiveIntegerField(
        default=1,
        help_text="1 is primary career goal, 2 is secondary, etc.",
    )
    target_term = models.ForeignKey(
        "academic_records.AcademicTerm",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_career_preferences"
        ordering = ["priority", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student_record", "career_objective"],
                name="unique_career_objective_per_student",
            ),
            models.UniqueConstraint(
                fields=["student_record", "priority"],
                name="unique_priority_per_student_career_preference",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_record.student.username} -> {self.career_objective.title} (Priority {self.priority})"

    def clean(self) -> None:
        super().clean()
        if (
            self.student_record_id
            and self.career_objective_id
            and self.student_record.institution_id != self.career_objective.institution_id
        ):
            raise ValidationError(
                {"career_objective": "Career objective must belong to the student's institution."}
            )
        if (
            self.target_term is not None
            and self.target_term.institution_id != self.institution_id
        ):
            raise ValidationError(
                {"target_term": "Target academic term must belong to the student's institution."}
            )

