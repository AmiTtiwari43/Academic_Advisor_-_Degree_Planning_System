"""
Builder for CurriculumGraph from raw data, AST rule JSONs, or course catalogs.
Pure Python. Zero Django imports.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from curriculum.graph.graph import CurriculumGraph
from curriculum.graph.models import (
    DependencyType,
    GraphEdge,
    GraphNode,
)


def _extract_edges_from_ast(
    course_code: str,
    node: Any,
    group_type: str = "all_of",
    group_id: str | None = None,
) -> list[GraphEdge]:
    """Recursively walks a rule AST and constructs typed GraphEdge objects."""
    edges: list[GraphEdge] = []
    if not isinstance(node, dict):
        return edges

    op_type = node.get("type")

    if op_type == "course_completed":
        ref_code = node.get("course_code")
        if isinstance(ref_code, str) and ref_code.strip():
            edges.append(
                GraphEdge(
                    dependent=course_code,
                    prerequisite=ref_code,
                    dependency_type=DependencyType.PREREQUISITE,
                    min_grade=node.get("min_grade"),
                    group_type=group_type,
                    group_id=group_id,
                )
            )

    elif op_type == "corequisite":
        ref_code = node.get("course_code")
        if isinstance(ref_code, str) and ref_code.strip():
            edges.append(
                GraphEdge(
                    dependent=course_code,
                    prerequisite=ref_code,
                    dependency_type=DependencyType.COREQUISITE,
                    group_type=group_type,
                    group_id=group_id,
                )
            )

    elif op_type == "anti_requisite":
        ref_code = node.get("course_code")
        if isinstance(ref_code, str) and ref_code.strip():
            edges.append(
                GraphEdge(
                    dependent=course_code,
                    prerequisite=ref_code,
                    dependency_type=DependencyType.ANTI_REQUISITE,
                    group_type=group_type,
                    group_id=group_id,
                )
            )

    elif op_type == "any_of":
        # Any_of branch creates an alternative group ID
        branch_group_id = f"any_of_{uuid.uuid4().hex[:8]}"
        conditions = node.get("conditions", [])
        if isinstance(conditions, list):
            for child in conditions:
                edges.extend(
                    _extract_edges_from_ast(
                        course_code=course_code,
                        node=child,
                        group_type="any_of",
                        group_id=branch_group_id,
                    )
                )

    elif op_type == "all_of":
        conditions = node.get("conditions", [])
        if isinstance(conditions, list):
            for child in conditions:
                edges.extend(
                    _extract_edges_from_ast(
                        course_code=course_code,
                        node=child,
                        group_type="all_of",
                        group_id=None,
                    )
                )

    return edges


def build_graph_from_rules(
    courses: list[dict[str, Any]],
    rules: Mapping[str, dict[str, Any]] | list[dict[str, Any]],
) -> CurriculumGraph:
    """
    Builds a CurriculumGraph from list of course definitions and rule ASTs.

    courses: list of dicts with at least {"code": "CS101", ...}
    rules: mapping of course_code -> rule_json, OR list of dicts {"course_code": "...", "rule_json": ...}
    """
    graph = CurriculumGraph()

    # 1. Register course nodes
    for c in courses:
        code = str(c.get("code", "")).strip().upper()
        if not code:
            continue
        node = GraphNode(
            code=code,
            title=str(c.get("title", "")),
            credits=float(c.get("credits", 0.0)),
            is_offered=bool(c.get("is_offered", True)),
            metadata=c.get("metadata", {}),
        )
        graph.add_node(node)

    # 2. Parse rules and register dependency edges
    rule_items: list[tuple[str, dict[str, Any]]] = []
    if isinstance(rules, Mapping):
        rule_items = [(k, v) for k, v in rules.items()]
    else:
        for item in rules:
            c_code = item.get("course_code") or item.get("code")
            r_json = item.get("rule_json") or item.get("rule", {})
            if c_code:
                rule_items.append((c_code, r_json))

    for course_code, rule_json in rule_items:
        edges = _extract_edges_from_ast(course_code, rule_json)
        for edge in edges:
            graph.add_edge(edge)

    return graph
