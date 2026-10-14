"""
Graph Traversal Algorithms for Curriculum Dependency Graphs.
Includes Cycle Detection with path reporting, Topological Sort,
Upstream/Downstream dependency chains, Explainable Paths, and Bounded Traversal.
Pure Python. Zero Django imports.
"""

from __future__ import annotations

from collections import deque
from typing import Iterable

from curriculum.graph.graph import CurriculumGraph
from curriculum.graph.models import (
    CycleResult,
    DependencyChainStep,
    DependencyType,
    ExplainablePath,
    GraphEdge,
)


class CycleDetectedError(ValueError):
    """Raised when an operation requiring an acyclic graph encounters a cycle."""

    def __init__(self, message: str, cycle_path: list[str]):
        super().__init__(message)
        self.cycle_path = cycle_path


class MaxDepthExceededError(ValueError):
    """Raised when graph traversal exceeds maximum allowed search depth."""


class MaxNodesExceededError(ValueError):
    """Raised when graph traversal visits more than maximum allowed nodes."""


DEFAULT_MAX_DEPTH = 30
DEFAULT_MAX_NODES = 5000


def detect_cycles(
    graph: CurriculumGraph,
    dependency_types: Iterable[DependencyType] | None = None,
) -> CycleResult:
    """
    Detects cycles in the curriculum prerequisite/corequisite dependency graph.
    Returns CycleResult containing boolean status, exact cycle paths, and primary cycle.

    Dependency edge: `dependent` -> `prerequisite`.
    A cycle means course A depends on course B which (transitively) depends on course A.
    Self-loops (A depends on A) are also detected and reported as ['A', 'A'].
    """
    if dependency_types is None:
        target_types = {DependencyType.PREREQUISITE, DependencyType.COREQUISITE}
    else:
        target_types = set(dependency_types)

    # 0 = WHITE (unvisited), 1 = GREY (in current DFS stack), 2 = BLACK (fully processed)
    state: dict[str, int] = {}
    parent_map: dict[str, str] = {}
    cycles: list[list[str]] = []

    # Get all nodes and referenced courses
    all_codes = set(graph.nodes.keys())
    for edge in graph.get_all_edges():
        if edge.dependency_type in target_types:
            all_codes.add(edge.dependent)
            all_codes.add(edge.prerequisite)

    # Deterministic iteration order
    sorted_codes = sorted(all_codes)
    for code in sorted_codes:
        state[code] = 0

    def dfs(node: str, current_path: list[str]) -> None:
        state[node] = 1  # GREY
        current_path.append(node)

        # Look at courses this node requires
        for edge in graph.get_prerequisite_edges(node):
            if edge.dependency_type not in target_types:
                continue
            neighbor = edge.prerequisite

            # Self-loop check
            if neighbor == node:
                cycle = [node, node]
                if cycle not in cycles:
                    cycles.append(cycle)
                continue

            neighbor_state = state.get(neighbor, 0)
            if neighbor_state == 1:
                # Found cycle: neighbor is in current recursion stack
                if neighbor in current_path:
                    start_idx = current_path.index(neighbor)
                    cycle = current_path[start_idx:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)
            elif neighbor_state == 0:
                parent_map[neighbor] = node
                dfs(neighbor, current_path)

        current_path.pop()
        state[node] = 2  # BLACK

    for code in sorted_codes:
        if state[code] == 0:
            dfs(code, [])

    if cycles:
        return CycleResult(
            has_cycle=True,
            cycles=cycles,
            primary_cycle=cycles[0],
        )

    return CycleResult(has_cycle=False, cycles=[], primary_cycle=None)


def topological_sort(
    graph: CurriculumGraph,
    dependency_types: Iterable[DependencyType] | None = None,
) -> list[str]:
    """
    Computes a topological ordering of courses using Kahn's algorithm.
    Prerequisites appear BEFORE the courses that depend on them.
    If the graph contains cycles, raises CycleDetectedError with the cycle path.
    """
    cycle_check = detect_cycles(graph, dependency_types)
    if cycle_check.has_cycle and cycle_check.primary_cycle:
        raise CycleDetectedError(
            f"Cannot topologically sort cyclic graph: {cycle_check.cycle_path_str}",
            cycle_path=cycle_check.primary_cycle,
        )

    if dependency_types is None:
        target_types = {DependencyType.PREREQUISITE, DependencyType.COREQUISITE}
    else:
        target_types = set(dependency_types)

    # In-degree here is count of prerequisites needed
    # We want prerequisites (in-degree 0) output first
    in_degrees: dict[str, int] = {}
    unlock_map: dict[str, list[str]] = {}

    all_nodes = set(graph.nodes.keys())
    for edge in graph.get_all_edges():
        if edge.dependency_type in target_types:
            all_nodes.add(edge.dependent)
            all_nodes.add(edge.prerequisite)

    for code in all_nodes:
        in_degrees[code] = 0
        unlock_map[code] = []

    for code in all_nodes:
        prereqs = [
            e.prerequisite
            for e in graph.get_prerequisite_edges(code)
            if e.dependency_type in target_types
        ]
        in_degrees[code] = len(prereqs)
        for p in prereqs:
            unlock_map[p].append(code)

    # Queue courses with no prerequisites
    ready_queue: deque[str] = deque(sorted([c for c, deg in in_degrees.items() if deg == 0]))
    sorted_result: list[str] = []

    while ready_queue:
        curr = ready_queue.popleft()
        sorted_result.append(curr)

        for dependent in sorted(unlock_map.get(curr, [])):
            in_degrees[dependent] -= 1
            if in_degrees[dependent] == 0:
                ready_queue.append(dependent)

    if len(sorted_result) != len(all_nodes):
        # Fallback if any unvisited due to unexpected cycle
        unvisited = sorted(list(all_nodes - set(sorted_result)))
        raise CycleDetectedError(
            f"Graph cycle prevented full topological ordering. Unordered nodes: {unvisited}",
            cycle_path=unvisited,
        )

    return sorted_result


def get_upstream_dependencies(
    graph: CurriculumGraph,
    start_code: str,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
    dependency_types: Iterable[DependencyType] | None = None,
) -> list[str]:
    """
    Traverses upstream dependencies (prerequisites and corequisites) of start_code.
    Returns list of course codes in breadth-first order (closest first).
    Enforces max_depth and max_nodes bounded traversal guards.
    """
    start_code = start_code.strip().upper()
    if dependency_types is None:
        target_types = {DependencyType.PREREQUISITE, DependencyType.COREQUISITE}
    else:
        target_types = set(dependency_types)

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_code, 0)])
    result: list[str] = []

    while queue:
        curr, depth = queue.popleft()

        if depth > max_depth:
            raise MaxDepthExceededError(
                f"Traversal exceeded max depth {max_depth} at course {curr}."
            )

        if len(visited) > max_nodes:
            raise MaxNodesExceededError(
                f"Traversal visited more than {max_nodes} nodes starting from {start_code}."
            )

        for edge in graph.get_prerequisite_edges(curr):
            if edge.dependency_type not in target_types:
                continue
            prereq = edge.prerequisite
            if prereq not in visited and prereq != start_code:
                visited.add(prereq)
                result.append(prereq)
                queue.append((prereq, depth + 1))

    return result


def get_downstream_dependents(
    graph: CurriculumGraph,
    start_code: str,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
    dependency_types: Iterable[DependencyType] | None = None,
) -> list[str]:
    """
    Traverses downstream dependents (courses unlocked by start_code).
    Returns list of unlocked course codes in breadth-first order.
    Enforces max_depth and max_nodes bounded traversal guards.
    """
    start_code = start_code.strip().upper()
    if dependency_types is None:
        target_types = {DependencyType.PREREQUISITE, DependencyType.COREQUISITE}
    else:
        target_types = set(dependency_types)

    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_code, 0)])
    result: list[str] = []

    while queue:
        curr, depth = queue.popleft()

        if depth > max_depth:
            raise MaxDepthExceededError(
                f"Traversal exceeded max depth {max_depth} at course {curr}."
            )

        if len(visited) > max_nodes:
            raise MaxNodesExceededError(
                f"Traversal visited more than {max_nodes} nodes starting from {start_code}."
            )

        for edge in graph.get_unlock_edges(curr):
            if edge.dependency_type not in target_types:
                continue
            dependent = edge.dependent
            if dependent not in visited and dependent != start_code:
                visited.add(dependent)
                result.append(dependent)
                queue.append((dependent, depth + 1))

    return result


def get_explainable_paths(
    graph: CurriculumGraph,
    target_code: str,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> list[ExplainablePath]:
    """
    Computes all prerequisite paths from target_code back to foundational root courses.
    Provides structured steps and plain-English explanation of why each is required.
    """
    target_code = target_code.strip().upper()
    paths: list[list[GraphEdge]] = []
    visited_nodes = 0

    def dfs_paths(current_code: str, current_edges: list[GraphEdge], current_depth: int) -> None:
        nonlocal visited_nodes
        visited_nodes += 1
        if visited_nodes > max_nodes:
            raise MaxNodesExceededError(f"Exceeded max nodes {max_nodes} during path exploration.")
        if current_depth > max_depth:
            raise MaxDepthExceededError(f"Exceeded max depth {max_depth} during path exploration.")

        prereq_edges = [
            e for e in graph.get_prerequisite_edges(current_code)
            if e.dependency_type in (DependencyType.PREREQUISITE, DependencyType.COREQUISITE)
        ]

        if not prereq_edges:
            # Reached a root course
            if current_edges:
                paths.append(list(current_edges))
            return

        for edge in prereq_edges:
            # Guard against cycles
            edge_chain_nodes = [e.dependent for e in current_edges]
            if edge.prerequisite in edge_chain_nodes:
                continue  # Skip cyclic path

            current_edges.append(edge)
            dfs_paths(edge.prerequisite, current_edges, current_depth + 1)
            current_edges.pop()

    dfs_paths(target_code, [], 0)

    explainable_paths: list[ExplainablePath] = []
    for edge_list in paths:
        path_codes = [target_code] + [e.prerequisite for e in edge_list]
        root_prereq = path_codes[-1]

        steps: list[DependencyChainStep] = []
        explanation_parts: list[str] = []

        for idx, edge in enumerate(edge_list):
            node = graph.get_node(edge.prerequisite)
            title = node.title if node else edge.prerequisite
            step = DependencyChainStep(
                course_code=edge.prerequisite,
                course_title=title,
                dependency_type=edge.dependency_type,
                min_grade=edge.min_grade,
                depth=idx + 1,
            )
            steps.append(step)

            grade_clause = f" with min grade {edge.min_grade}" if edge.min_grade else ""
            explanation_parts.append(
                f"{edge.dependent} requires {edge.prerequisite} ({edge.dependency_type.value}{grade_clause})"
            )

        explanation = " -> ".join(explanation_parts)

        explainable_paths.append(
            ExplainablePath(
                target_course=target_code,
                root_prerequisite=root_prereq,
                path=path_codes,
                steps=steps,
                explanation=explanation,
            )
        )

    return explainable_paths


def get_relevant_subgraph(
    graph: CurriculumGraph,
    target_code: str,
    upstream_depth: int = 2,
    downstream_depth: int = 1,
) -> CurriculumGraph:
    """
    Extracts a focused subgraph centered on target_code up to upstream_depth
    and downstream_depth.
    """
    target_code = target_code.strip().upper()
    subgraph = CurriculumGraph()

    target_node = graph.get_node(target_code)
    if target_node:
        subgraph.add_node(target_node)

    # Collect upstream nodes
    upstream_nodes: set[str] = {target_code}
    current_level = {target_code}
    for _ in range(upstream_depth):
        next_level: set[str] = set()
        for c in current_level:
            for edge in graph.get_prerequisite_edges(c):
                next_level.add(edge.prerequisite)
        upstream_nodes.update(next_level)
        current_level = next_level

    # Collect downstream nodes
    downstream_nodes: set[str] = {target_code}
    current_level = {target_code}
    for _ in range(downstream_depth):
        next_downstream_level: set[str] = set()
        for c in current_level:
            for edge in graph.get_unlock_edges(c):
                next_downstream_level.add(edge.dependent)
        downstream_nodes.update(next_downstream_level)
        current_level = next_downstream_level

    included_codes = upstream_nodes | downstream_nodes

    # Add all collected nodes
    for code in included_codes:
        node = graph.get_node(code)
        if node:
            subgraph.add_node(node)

    # Add connecting edges
    for code in included_codes:
        for edge in graph.get_prerequisite_edges(code):
            if edge.prerequisite in included_codes:
                subgraph.add_edge(edge)

    return subgraph
