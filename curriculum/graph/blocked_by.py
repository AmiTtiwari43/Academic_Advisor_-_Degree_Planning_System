"""
Blocked-By Computation for Curriculum Dependency Graph.
Evaluates which direct and transitive prerequisites block a student from taking a course.
Pure Python. Zero Django imports.
"""

from __future__ import annotations

from typing import Mapping

from curriculum.graph.graph import CurriculumGraph
from curriculum.graph.models import (
    BlockedByResult,
    BlockedReason,
    DependencyType,
    GraphEdge,
)

# Standard default grade ranking where higher rank = better grade
DEFAULT_GRADE_RANK: dict[str, int] = {
    "A+": 12,
    "A": 11,
    "A-": 10,
    "B+": 9,
    "B": 8,
    "B-": 7,
    "C+": 6,
    "C": 5,
    "C-": 4,
    "D+": 3,
    "D": 2,
    "F": 1,
}


def _is_grade_sufficient(
    student_grade: str | None,
    min_grade: str | None,
    grade_rank: Mapping[str, int] = DEFAULT_GRADE_RANK,
) -> bool:
    """Checks if student grade meets or exceeds required min_grade."""
    if not min_grade:
        return True
    if not student_grade:
        return False
    s_rank = grade_rank.get(student_grade.strip().upper(), -1)
    m_rank = grade_rank.get(min_grade.strip().upper(), -1)
    if s_rank == -1 or m_rank == -1:
        # Fallback to direct string equality if not in standard scale
        return student_grade.strip().upper() == min_grade.strip().upper()
    return s_rank >= m_rank


def compute_blocked_by(
    graph: CurriculumGraph,
    target_code: str,
    completed_courses: Mapping[str, str] | set[str] | list[str],
    in_progress_courses: set[str] | list[str] | None = None,
    waived_courses: set[str] | list[str] | None = None,
    grade_rank: Mapping[str, int] = DEFAULT_GRADE_RANK,
) -> BlockedByResult:
    """
    Computes which courses currently block a student from enrolling in target_code.

    Parameters:
    - graph: CurriculumGraph instance.
    - target_code: Course code to evaluate.
    - completed_courses: Dict mapping course_code -> grade string (e.g. {"CS101": "B"}),
      or set/list of completed course codes (treated as grade "A").
    - in_progress_courses: Courses currently in progress (satisfies corequisite, but not prerequisite).
    - waived_courses: Courses waived by an authorized advisor override.
    - grade_rank: Map of grade string to integer rank for comparison.
    """
    target_code = target_code.strip().upper()

    # Normalize inputs
    completed_map: dict[str, str] = {}
    if isinstance(completed_courses, Mapping):
        completed_map = {k.strip().upper(): str(v).strip().upper() for k, v in completed_courses.items()}
    else:
        completed_map = {c.strip().upper(): "A" for c in completed_courses}

    in_progress = {c.strip().upper() for c in (in_progress_courses or [])}
    waived = {c.strip().upper() for c in (waived_courses or [])}

    direct_blockers: list[BlockedReason] = []
    indirect_blockers: list[BlockedReason] = []
    all_blocking_courses: set[str] = set()

    # 1. Check direct dependencies of target_code
    direct_edges = graph.get_prerequisite_edges(target_code)

    # Group edges by group_id for any_of handling
    grouped_edges: dict[str | None, list[GraphEdge]] = {}
    for edge in direct_edges:
        key = edge.group_id if edge.group_type == "any_of" else None
        if key not in grouped_edges:
            grouped_edges[key] = []
        grouped_edges[key].append(edge)

    # Helper to check a single edge
    def evaluate_edge(edge: GraphEdge) -> tuple[bool, str, str | None]:
        """Returns (is_satisfied, status_reason, student_grade)."""
        req = edge.prerequisite

        if req in waived:
            return True, "waived", None

        if edge.dependency_type == DependencyType.ANTI_REQUISITE:
            if req in completed_map or req in in_progress:
                return False, "anti_requisite_present", completed_map.get(req)
            return True, "satisfied", None

        if edge.dependency_type == DependencyType.COREQUISITE:
            if req in completed_map:
                grade = completed_map[req]
                if _is_grade_sufficient(grade, edge.min_grade, grade_rank):
                    return True, "completed", grade
                return False, "grade_too_low", grade
            if req in in_progress:
                return True, "in_progress", None
            return False, "not_attempted", None

        # Standard PREREQUISITE
        if req in completed_map:
            grade = completed_map[req]
            if _is_grade_sufficient(grade, edge.min_grade, grade_rank):
                return True, "completed", grade
            return False, "grade_too_low", grade

        if req in in_progress:
            return False, "in_progress_not_earned", None

        return False, "not_attempted", None

    # Evaluate direct groups
    for group_id, edges in grouped_edges.items():
        if group_id is not None:
            # any_of group: at least one edge must be satisfied
            any_satisfied = False
            group_reasons: list[tuple[GraphEdge, str, str | None]] = []
            for edge in edges:
                sat, reason_code, s_grade = evaluate_edge(edge)
                if sat:
                    any_satisfied = True
                    break
                group_reasons.append((edge, reason_code, s_grade))

            if not any_satisfied:
                # All options failed, report the group courses as blockers
                for edge, reason_code, s_grade in group_reasons:
                    all_blocking_courses.add(edge.prerequisite)
                    direct_blockers.append(
                        BlockedReason(
                            course_code=target_code,
                            missing_prerequisite=edge.prerequisite,
                            dependency_type=edge.dependency_type,
                            required_min_grade=edge.min_grade,
                            student_status=reason_code,
                            student_grade=s_grade,
                            is_direct=True,
                            blocking_chain=[target_code, edge.prerequisite],
                            message=f"Missing elective prerequisite {edge.prerequisite} from group ({reason_code}).",
                        )
                    )
        else:
            # all_of edges: all must be satisfied
            for edge in edges:
                sat, reason_code, s_grade = evaluate_edge(edge)
                if not sat:
                    all_blocking_courses.add(edge.prerequisite)
                    grade_clause = f" with min grade {edge.min_grade}" if edge.min_grade else ""
                    msg = (
                        f"Requires {edge.prerequisite}{grade_clause}, but student status is {reason_code}."
                        if edge.dependency_type != DependencyType.ANTI_REQUISITE
                        else f"Enrollment blocked: anti-requisite {edge.prerequisite} already completed or in-progress."
                    )
                    direct_blockers.append(
                        BlockedReason(
                            course_code=target_code,
                            missing_prerequisite=edge.prerequisite,
                            dependency_type=edge.dependency_type,
                            required_min_grade=edge.min_grade,
                            student_status=reason_code,
                            student_grade=s_grade,
                            is_direct=True,
                            blocking_chain=[target_code, edge.prerequisite],
                            message=msg,
                        )
                    )

    # 2. Check indirect (transitive) dependencies of direct blockers
    # Trace upstream prerequisites for each direct blocker
    for direct_blocker in list(direct_blockers):
        missing_course = direct_blocker.missing_prerequisite
        # Find what blocks missing_course
        upstream_edges = graph.get_prerequisite_edges(missing_course)
        for u_edge in upstream_edges:
            if u_edge.dependency_type not in (DependencyType.PREREQUISITE, DependencyType.COREQUISITE):
                continue
            u_req = u_edge.prerequisite
            sat, r_code, s_grade = evaluate_edge(u_edge)
            if not sat:
                all_blocking_courses.add(u_req)
                indirect_blockers.append(
                    BlockedReason(
                        course_code=target_code,
                        missing_prerequisite=u_req,
                        dependency_type=u_edge.dependency_type,
                        required_min_grade=u_edge.min_grade,
                        student_status=r_code,
                        student_grade=s_grade,
                        is_direct=False,
                        blocking_chain=[target_code, missing_course, u_req],
                        message=f"Indirect blocker: {u_req} is required before taking {missing_course} ({r_code}).",
                    )
                )

    # Direct unlocked courses if target_code is completed
    unlocked = [
        e.dependent
        for e in graph.get_unlock_edges(target_code)
        if e.dependency_type in (DependencyType.PREREQUISITE, DependencyType.COREQUISITE)
    ]

    is_blocked = len(direct_blockers) > 0

    return BlockedByResult(
        course_code=target_code,
        is_blocked=is_blocked,
        direct_blockers=direct_blockers,
        indirect_blockers=indirect_blockers,
        all_blocking_courses=all_blocking_courses,
        unlocked_courses=unlocked,
    )
