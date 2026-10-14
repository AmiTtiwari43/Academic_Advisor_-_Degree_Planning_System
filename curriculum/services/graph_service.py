"""
Curriculum Graph Service.
Django ORM integration layer connecting CurriculumVersion and PrerequisiteRule
models with the pure-Python curriculum.graph engine.
"""

from __future__ import annotations

from typing import Any

from academic_records.models import StudentRecord
from curriculum.graph import (
    BlockedByResult,
    CurriculumGraph,
    ExplainablePath,
    build_graph_from_rules,
    compute_blocked_by,
    generate_visualization_payload,
    get_explainable_paths,
    get_relevant_subgraph,
)
from curriculum.models import CurriculumVersion


def build_curriculum_version_graph(version: CurriculumVersion) -> CurriculumGraph:
    """
    Constructs a CurriculumGraph for all courses and prerequisite rules
    associated with a specific CurriculumVersion.
    """
    # 1. Collect all courses in the version
    # Courses can be attached to requirement groups or have prerequisite rules
    course_data: dict[str, dict[str, Any]] = {}

    # From requirement groups
    for group in version.requirement_groups.prefetch_related("group_courses__course").all():
        for gc in group.group_courses.all():
            course = gc.course
            code = course.code.strip().upper()
            if code not in course_data:
                course_data[code] = {
                    "code": code,
                    "title": course.title,
                    "credits": float(course.credits),
                    "is_offered": course.is_active,
                    "metadata": {
                        "course_id": str(course.id),
                        "group_id": str(group.id),
                        "group_name": group.name,
                    },
                }

    # Also include any courses directly having prerequisite rules in this version
    rules = list(version.prerequisite_rules.select_related("course").all())
    for rule in rules:
        c = rule.course
        code = c.code.strip().upper()
        if code not in course_data:
            course_data[code] = {
                "code": code,
                "title": c.title,
                "credits": float(c.credits),
                "is_offered": c.is_active,
                "metadata": {"course_id": str(c.id)},
            }

    # 2. Extract rules list
    rule_list = [{"code": r.course.code, "rule_json": r.rule_json} for r in rules]

    return build_graph_from_rules(list(course_data.values()), rule_list)


def get_course_dependency_paths(
    version: CurriculumVersion,
    course_code: str,
    max_depth: int = 30,
    max_nodes: int = 5000,
) -> list[ExplainablePath]:
    """Computes all explainable prerequisite chains for course_code in the version."""
    graph = build_curriculum_version_graph(version)
    return get_explainable_paths(graph, course_code, max_depth=max_depth, max_nodes=max_nodes)


def get_course_subgraph_visualization(
    version: CurriculumVersion,
    course_code: str,
    upstream_depth: int = 2,
    downstream_depth: int = 1,
) -> dict[str, str]:
    """Generates SVG and accessible text transcript for a focused course subgraph."""
    graph = build_curriculum_version_graph(version)
    subgraph = get_relevant_subgraph(
        graph,
        course_code,
        upstream_depth=upstream_depth,
        downstream_depth=downstream_depth,
    )
    return generate_visualization_payload(subgraph, target_code=course_code)


def get_student_blocked_by(
    version: CurriculumVersion,
    course_code: str,
    student_record: StudentRecord,
) -> BlockedByResult:
    """
    Evaluates which prerequisites block an enrolled student from taking course_code.
    Gathers completed transcript entries, in-progress entries, and authorized waivers.
    """
    graph = build_curriculum_version_graph(version)

    # Completed courses with grades
    completed_entries = student_record.transcript_entries.filter(
        status__in=["completed", "COMPLETED"],
        verification_status__in=["verified", "VERIFIED", "OFFICIAL_SEALED"],
    ).select_related("course")

    completed_courses: dict[str, str] = {
        entry.course.code.strip().upper(): entry.grade for entry in completed_entries
    }

    # In-progress courses
    in_progress_entries = student_record.transcript_entries.filter(
        status__in=["in_progress", "IN_PROGRESS"]
    ).select_related("course")
    in_progress = {entry.course.code.strip().upper() for entry in in_progress_entries}

    return compute_blocked_by(
        graph=graph,
        target_code=course_code,
        completed_courses=completed_courses,
        in_progress_courses=in_progress,
        waived_courses=set(),
    )
