"""
Core CurriculumGraph class for storing and querying directed curriculum dependencies.
Pure Python. Zero Django imports.
"""

from __future__ import annotations

from curriculum.graph.models import (
    DependencyType,
    GraphEdge,
    GraphNode,
)


class CurriculumGraph:
    """
    Directed Graph representing curriculum courses and requirement relationships.

    Edges directed from dependent (course needing prerequisite) to prerequisite.
    Also indexes reverse edges (unlocks) for rapid downstream queries.
    """

    def __init__(self):
        self._nodes: dict[str, GraphNode] = {}
        # dependent -> list of edges pointing to prerequisites
        self._prereq_edges: dict[str, list[GraphEdge]] = {}
        # prerequisite -> list of edges pointing to dependents (unlocks)
        self._unlock_edges: dict[str, list[GraphEdge]] = {}
        # Set of course codes referenced as prerequisites but missing from nodes
        self._referenced_courses: set[str] = set()

    def add_node(self, node: GraphNode) -> None:
        """Adds a course node to the graph."""
        code = node.code
        self._nodes[code] = node
        if code not in self._prereq_edges:
            self._prereq_edges[code] = []
        if code not in self._unlock_edges:
            self._unlock_edges[code] = []

    def get_node(self, code: str) -> GraphNode | None:
        """Retrieves a course node by code, case-insensitively."""
        return self._nodes.get(code.strip().upper())

    def has_node(self, code: str) -> bool:
        """Checks if a course code is a registered node."""
        return code.strip().upper() in self._nodes

    def add_edge(self, edge: GraphEdge) -> None:
        """
        Adds a directed dependency edge.
        `edge.dependent` requires `edge.prerequisite`.
        """
        dep = edge.dependent
        req = edge.prerequisite

        self._referenced_courses.add(dep)
        self._referenced_courses.add(req)

        # Initialize lists if nodes haven't been added yet
        if dep not in self._prereq_edges:
            self._prereq_edges[dep] = []
        if req not in self._unlock_edges:
            self._unlock_edges[req] = []

        # Avoid duplicate identical edges
        for existing in self._prereq_edges[dep]:
            if (
                existing.prerequisite == req
                and existing.dependency_type == edge.dependency_type
                and existing.min_grade == edge.min_grade
                and existing.group_id == edge.group_id
            ):
                return

        self._prereq_edges[dep].append(edge)
        self._unlock_edges[req].append(edge)

    def get_prerequisite_edges(
        self,
        code: str,
        dependency_type: DependencyType | None = None,
    ) -> list[GraphEdge]:
        """Gets all edges representing prerequisites for a given course."""
        code = code.strip().upper()
        edges = self._prereq_edges.get(code, [])
        if dependency_type is not None:
            return [e for e in edges if e.dependency_type == dependency_type]
        return list(edges)

    def get_unlock_edges(
        self,
        code: str,
        dependency_type: DependencyType | None = None,
    ) -> list[GraphEdge]:
        """Gets all edges representing courses unlocked by a given prerequisite."""
        code = code.strip().upper()
        edges = self._unlock_edges.get(code, [])
        if dependency_type is not None:
            return [e for e in edges if e.dependency_type == dependency_type]
        return list(edges)

    def get_direct_prerequisites(self, code: str) -> list[str]:
        """Returns direct prerequisite course codes for a course."""
        return [
            e.prerequisite
            for e in self.get_prerequisite_edges(code)
            if e.dependency_type in (DependencyType.PREREQUISITE, DependencyType.COREQUISITE)
        ]

    def get_direct_unlocks(self, code: str) -> list[str]:
        """Returns direct courses unlocked by this course."""
        return [
            e.dependent
            for e in self.get_unlock_edges(code)
            if e.dependency_type in (DependencyType.PREREQUISITE, DependencyType.COREQUISITE)
        ]

    @property
    def nodes(self) -> dict[str, GraphNode]:
        """Read-only view of all nodes."""
        return dict(self._nodes)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._prereq_edges.values())

    def get_missing_course_references(self) -> list[str]:
        """
        Returns course codes referenced in edges that do not exist as nodes.
        Sorted alphabetically.
        """
        missing = self._referenced_courses - set(self._nodes.keys())
        return sorted(list(missing))

    def get_all_edges(self) -> list[GraphEdge]:
        """Returns flat list of all edges in the graph."""
        all_edges: list[GraphEdge] = []
        for edges in self._prereq_edges.values():
            all_edges.extend(edges)
        return all_edges
