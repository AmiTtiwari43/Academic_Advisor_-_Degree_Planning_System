"""
Curriculum Publishing & Preview Service.
Provides pre-publication validation, atomic state transition to PUBLISHED,
and publish preview summaries.
"""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from curriculum.models import CurriculumStatus, CurriculumVersion
from curriculum.services.validation_service import (
    validate_curriculum_version,
)


def get_publish_preview(version: CurriculumVersion) -> dict[str, Any]:
    """
    Summarizes the contents and validation status of a curriculum version prior to publication.
    """
    report = validate_curriculum_version(version)

    total_courses = version.requirement_groups.values("courses").distinct().count()
    total_groups = version.requirement_groups.count()
    total_rules = version.prerequisite_rules.count()

    return {
        "curriculum_version_id": str(version.id),
        "programme_code": version.programme.code,
        "programme_name": version.programme.name,
        "version_number": version.version_number,
        "academic_year": version.academic_year,
        "total_credits_required": float(version.total_credits_required),
        "min_cgpa_required": float(version.min_cgpa_required),
        "total_requirement_groups": total_groups,
        "total_unique_courses": total_courses,
        "total_prerequisite_rules": total_rules,
        "can_publish": report.is_valid,
        "validation_report": report.to_dict(),
    }


def publish_curriculum_version(version: CurriculumVersion, user: Any) -> CurriculumVersion:
    """
    Validates and atomically transitions a draft curriculum version to PUBLISHED.
    Raises ValidationError if the version is not a draft or fails validation.
    """
    if version.status != CurriculumStatus.DRAFT:
        raise ValidationError(
            f"Only DRAFT curriculum versions can be published. Current status is {version.status}."
        )

    # Pre-publication validation
    report = validate_curriculum_version(version)
    if not report.is_valid:
        error_msgs = "; ".join(e.message for e in report.errors)
        raise ValidationError(
            f"Pre-publication validation failed with {len(report.errors)} errors: {error_msgs}"
        )

    with transaction.atomic():
        version.status = CurriculumStatus.PUBLISHED
        version.published_by = user
        version.published_at = timezone.now()
        version.save()

    return version
