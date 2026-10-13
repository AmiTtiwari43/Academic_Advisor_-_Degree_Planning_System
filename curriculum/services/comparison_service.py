"""
Curriculum Version Comparison Service.
Computes fine-grained differences between two curriculum versions:
metadata changes, added/removed/modified requirement groups, courses, and prerequisite rules.
"""

from typing import Any

from curriculum.models import CurriculumVersion


def compare_curriculum_versions(v1: CurriculumVersion, v2: CurriculumVersion) -> dict[str, Any]:
    """
    Compares two curriculum versions and returns structured diff information.
    v1 is the base version, v2 is the target/newer version.
    """
    # 1. Metadata diff
    metadata_diff = {
        "v1": {
            "version_number": v1.version_number,
            "academic_year": v1.academic_year,
            "status": v1.status,
            "total_credits_required": float(v1.total_credits_required),
            "min_cgpa_required": float(v1.min_cgpa_required),
        },
        "v2": {
            "version_number": v2.version_number,
            "academic_year": v2.academic_year,
            "status": v2.status,
            "total_credits_required": float(v2.total_credits_required),
            "min_cgpa_required": float(v2.min_cgpa_required),
        },
        "credits_changed": v1.total_credits_required != v2.total_credits_required,
        "cgpa_changed": v1.min_cgpa_required != v2.min_cgpa_required,
    }

    # 2. Courses diff
    v1_courses = {
        c.code: {
            "code": c.code,
            "title": c.title,
            "credits": float(c.credits),
        }
        for g in v1.requirement_groups.prefetch_related("courses").all()
        for c in g.courses.all()
    }
    v2_courses = {
        c.code: {
            "code": c.code,
            "title": c.title,
            "credits": float(c.credits),
        }
        for g in v2.requirement_groups.prefetch_related("courses").all()
        for c in g.courses.all()
    }

    added_courses = [v2_courses[code] for code in v2_courses if code not in v1_courses]
    removed_courses = [v1_courses[code] for code in v1_courses if code not in v2_courses]

    # 3. Requirement groups diff
    v1_groups = {g.name: g for g in v1.requirement_groups.all()}
    v2_groups = {g.name: g for g in v2.requirement_groups.all()}

    added_groups = [
        {"name": name, "min_credits": float(g.min_credits), "type": g.group_type}
        for name, g in v2_groups.items()
        if name not in v1_groups
    ]
    removed_groups = [
        {"name": name, "min_credits": float(g.min_credits), "type": g.group_type}
        for name, g in v1_groups.items()
        if name not in v2_groups
    ]
    modified_groups = []
    for name in v1_groups:
        if name in v2_groups:
            g1 = v1_groups[name]
            g2 = v2_groups[name]
            if g1.min_credits != g2.min_credits or g1.group_type != g2.group_type:
                modified_groups.append(
                    {
                        "name": name,
                        "v1_min_credits": float(g1.min_credits),
                        "v2_min_credits": float(g2.min_credits),
                        "v1_type": g1.group_type,
                        "v2_type": g2.group_type,
                    }
                )

    # 4. Prerequisite rules diff
    v1_rules = {
        r.course.code: r.rule_json for r in v1.prerequisite_rules.select_related("course").all()
    }
    v2_rules = {
        r.course.code: r.rule_json for r in v2.prerequisite_rules.select_related("course").all()
    }

    added_rules = [code for code in v2_rules if code not in v1_rules]
    removed_rules = [code for code in v1_rules if code not in v2_rules]
    modified_rules = [
        code for code in v1_rules if code in v2_rules and v1_rules[code] != v2_rules[code]
    ]

    return {
        "metadata": metadata_diff,
        "courses": {
            "added": added_courses,
            "removed": removed_courses,
            "common_count": len(set(v1_courses.keys()) & set(v2_courses.keys())),
        },
        "requirement_groups": {
            "added": added_groups,
            "removed": removed_groups,
            "modified": modified_groups,
        },
        "prerequisite_rules": {
            "added": added_rules,
            "removed": removed_rules,
            "modified": modified_rules,
        },
    }
