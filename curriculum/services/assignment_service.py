"""
Student Curriculum Assignment Service.
Pins students to published curriculum versions for their degree programmes,
enforcing multi-tenant boundary checks and active assignment exclusivity.
"""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from curriculum.models import (
    CurriculumStatus,
    CurriculumVersion,
    StudentCurriculumAssignment,
)


def assign_student_to_curriculum(
    student: Any,
    curriculum_version: CurriculumVersion,
    assigned_by: Any | None = None,
) -> StudentCurriculumAssignment:
    """
    Assigns a student to an authoritative published curriculum version.
    """
    if curriculum_version.status != CurriculumStatus.PUBLISHED:
        raise ValidationError(
            f"Cannot assign student to unpublished curriculum version with status '{curriculum_version.status}'. "
            "Only PUBLISHED versions may be assigned."
        )

    # Verify student membership in the version's institution
    is_member = student.institution_memberships.filter(
        institution=curriculum_version.institution, is_active=True
    ).exists()
    if not is_member:
        raise ValidationError(
            f"Student {student.username} does not have an active membership in institution "
            f"'{curriculum_version.institution.name}'."
        )

    with transaction.atomic():
        # Deactivate existing assignments for the same student and programme
        StudentCurriculumAssignment.objects.filter(
            student=student,
            curriculum_version__programme=curriculum_version.programme,
            is_active=True,
        ).update(is_active=False)

        assignment = StudentCurriculumAssignment.objects.create(
            institution=curriculum_version.institution,
            student=student,
            curriculum_version=curriculum_version,
            assigned_by=assigned_by,
            is_active=True,
        )

    return assignment
