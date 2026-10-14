"""
Infeasibility diagnosis and bottleneck identification for degree plan optimization.
Pure Python. Decoupled from Django ORM queries.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Sequence

from planning.optimizer.models import (
    OptimizationRequest,
    OptimizerCourse,
)


def diagnose_infeasibility(request: OptimizationRequest) -> list[str]:
    """
    Analyzes an optimization request and identifies specific, actionable reasons
    why a valid multi-term schedule cannot be constructed.

    Returns a list of human-readable blocking constraint descriptions.
    """
    blockers: list[str] = []

    available_terms = request.available_terms
    if not available_terms:
        return ["No academic terms were provided for scheduling."]

    num_terms = len(available_terms)
    term_seasons = {t.season.upper() for t in available_terms}

    # Filter out already satisfied courses
    satisfied_codes = set(request.completed_courses) | set(request.in_progress_courses)
    schedulable_courses = [
        c for c in request.courses_to_schedule if c.code not in satisfied_codes
    ]
    course_map = {c.code: c for c in schedulable_courses}
    all_known_codes = satisfied_codes | set(course_map.keys())

    mandatory_courses = [c for c in schedulable_courses if c.is_mandatory]

    # 1. Total credit demand vs cumulative term capacity
    total_mandatory_credits = sum(c.credits for c in mandatory_courses)
    total_capacity = sum(t.max_credits for t in available_terms)

    if total_mandatory_credits > total_capacity:
        blockers.append(
            f"Credit capacity deficit: Mandatory coursework requires {total_mandatory_credits:.1f} "
            f"credits, but the {num_terms} available terms provide a maximum capacity of "
            f"{total_capacity:.1f} credits (shortfall of {total_mandatory_credits - total_capacity:.1f} credits)."
        )

    # 2. Missing prerequisites for mandatory courses
    for course in mandatory_courses:
        for prereq in course.prerequisites:
            if prereq not in all_known_codes:
                blockers.append(
                    f"Missing prerequisite: Mandatory course {course.code} requires '{prereq}', "
                    f"which is neither completed nor present in the curriculum to schedule."
                )
        for coreq in course.corequisites:
            if coreq not in all_known_codes:
                blockers.append(
                    f"Missing corequisite: Mandatory course {course.code} requires corequisite '{coreq}', "
                    f"which is neither completed nor present in the curriculum to schedule."
                )

    # 3. Anti-requisite conflicts with completed coursework
    for course in mandatory_courses:
        for anti in course.anti_requisites:
            if anti in satisfied_codes:
                blockers.append(
                    f"Anti-requisite conflict: Mandatory course {course.code} cannot be scheduled "
                    f"because anti-requisite '{anti}' has already been completed or is in-progress."
                )

    # 4. Offering season mismatch
    for course in mandatory_courses:
        offered_seasons = {s.upper() for s in course.offered_seasons}
        if not offered_seasons.intersection(term_seasons):
            seasons_str = ", ".join(sorted(offered_seasons)) or "None"
            blockers.append(
                f"Season offering conflict: Mandatory course {course.code} is only offered in "
                f"[{seasons_str}], but none of the {num_terms} available terms cover these seasons."
            )

    # 5. Prerequisite chain depth exceeding available terms
    chain_blockers = _check_prerequisite_chain_depth(
        schedulable_courses=schedulable_courses,
        satisfied_codes=satisfied_codes,
        num_terms=num_terms,
    )
    blockers.extend(chain_blockers)

    # 6. Fallback if no specific structural violation identified
    if not blockers:
        blockers.append(
            f"Schedule infeasible: Academic constraints (term credit bounds "
            f"[{min(t.min_credits for t in available_terms):.1f}-{max(t.max_credits for t in available_terms):.1f}], "
            f"course seasonal offerings, and prerequisite sequencing) cannot be simultaneously "
            f"satisfied within {num_terms} terms."
        )

    return blockers


def _check_prerequisite_chain_depth(
    schedulable_courses: Sequence[OptimizerCourse],
    satisfied_codes: set[str],
    num_terms: int,
) -> list[str]:
    """Detects cycles or chains whose depth strictly exceeds the term count."""
    blockers: list[str] = []
    course_map = {c.code: c for c in schedulable_courses}

    # Build adjacency list: prerequisite -> dependent
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {c.code: 0 for c in schedulable_courses}

    for course in schedulable_courses:
        for prereq in course.prerequisites:
            if prereq in course_map:
                adj[prereq].append(course.code)
                in_degree[course.code] += 1

    # Cycle detection via Kahn's algorithm
    queue = deque([code for code, deg in in_degree.items() if deg == 0])
    visited_count = 0
    while queue:
        node = queue.popleft()
        visited_count += 1
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited_count < len(schedulable_courses):
        blockers.append(
            "Curriculum prerequisite cycle: A circular dependency exists among the schedulable "
            "courses, preventing chronological term ordering."
        )
        return blockers

    # Dynamic programming for longest path
    # Recompute in-degrees for topo sort
    in_deg: dict[str, int] = {c.code: 0 for c in schedulable_courses}
    for course in schedulable_courses:
        for prereq in course.prerequisites:
            if prereq in course_map:
                in_deg[course.code] += 1

    longest_path_to: dict[str, int] = {c.code: 1 for c in schedulable_courses}
    parent_of: dict[str, str | None] = {c.code: None for c in schedulable_courses}

    q = deque([code for code, deg in in_deg.items() if deg == 0])
    while q:
        curr = q.popleft()
        curr_dist = longest_path_to[curr]
        for neighbor in adj[curr]:
            if curr_dist + 1 > longest_path_to[neighbor]:
                longest_path_to[neighbor] = curr_dist + 1
                parent_of[neighbor] = curr
            in_deg[neighbor] -= 1
            if in_deg[neighbor] == 0:
                q.append(neighbor)

    for course in schedulable_courses:
        if course.is_mandatory and longest_path_to[course.code] > num_terms:
            # Reconstruct path
            path: list[str] = []
            node_curr: str | None = course.code
            while node_curr:
                path.append(node_curr)
                node_curr = parent_of.get(node_curr)
            path.reverse()
            path_str = " -> ".join(path)
            blockers.append(
                f"Prerequisite depth bottleneck: Mandatory chain ({path_str}) requires at least "
                f"{longest_path_to[course.code]} consecutive terms, but only {num_terms} terms are available."
            )

    return blockers
