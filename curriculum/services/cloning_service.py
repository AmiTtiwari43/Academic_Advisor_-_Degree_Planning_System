"""
Curriculum Version Cloning Service.
Deep copies an existing (published or draft) curriculum version into a new draft,
preserving hierarchical requirement groups, course memberships, and prerequisite rules.
"""

from typing import Any

from django.db import transaction
from django.db.models import Max

from curriculum.models import (
    CurriculumStatus,
    CurriculumVersion,
    PrerequisiteRule,
    RequirementGroup,
    RequirementGroupCourse,
)


def clone_curriculum_version(
    source_version: CurriculumVersion,
    user: Any,
    target_academic_year: str | None = None,
) -> CurriculumVersion:
    """
    Clones a curriculum version into a new DRAFT version with the next sequential version number.
    """
    with transaction.atomic():
        # Determine next version number for this programme
        max_ver = (
            CurriculumVersion.objects.filter(programme=source_version.programme).aggregate(
                Max("version_number")
            )["version_number__max"]
            or 0
        )
        new_version_number = max_ver + 1

        new_version = CurriculumVersion.objects.create(
            institution=source_version.institution,
            programme=source_version.programme,
            version_number=new_version_number,
            academic_year=target_academic_year or source_version.academic_year,
            status=CurriculumStatus.DRAFT,
            total_credits_required=source_version.total_credits_required,
            min_cgpa_required=source_version.min_cgpa_required,
            change_summary=f"Cloned from version {source_version.version_number}",
        )

        # Clone Requirement Groups preserving tree hierarchy
        old_to_new_group: dict[str, RequirementGroup] = {}

        # Fetch groups and sort topologically (root groups first)
        all_groups = list(source_version.requirement_groups.prefetch_related("group_courses").all())

        # Order groups: root groups first, then children
        def get_depth(g: RequirementGroup) -> int:
            d = 0
            curr = g
            while curr.parent_id:
                d += 1
                parent = next((p for p in all_groups if p.id == curr.parent_id), None)
                if not parent or d > 10:
                    break
                curr = parent
            return d

        all_groups.sort(key=get_depth)

        for old_g in all_groups:
            parent_new = old_to_new_group.get(str(old_g.parent_id)) if old_g.parent_id else None
            new_g = RequirementGroup.objects.create(
                institution=source_version.institution,
                curriculum_version=new_version,
                parent=parent_new,
                name=old_g.name,
                group_type=old_g.group_type,
                min_credits=old_g.min_credits,
                min_courses=old_g.min_courses,
                min_cgpa=old_g.min_cgpa,
                credit_category=old_g.credit_category,
                display_order=old_g.display_order,
            )
            old_to_new_group[str(old_g.id)] = new_g

            # Clone course memberships
            for rgc in old_g.group_courses.all():
                RequirementGroupCourse.objects.create(
                    requirement_group=new_g,
                    course=rgc.course,
                    is_mandatory=rgc.is_mandatory,
                    display_order=rgc.display_order,
                )

        # Clone Prerequisite Rules
        for old_rule in source_version.prerequisite_rules.all():
            PrerequisiteRule.objects.create(
                institution=source_version.institution,
                curriculum_version=new_version,
                course=old_rule.course,
                rule_json=old_rule.rule_json,
                description=old_rule.description,
            )

        return new_version
