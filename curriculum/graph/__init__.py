"""
Curriculum Prerequisite and Requirement Dependency Graph Package.
Pure Python. Decoupled from Django. Zero Django imports.
"""

from curriculum.graph.blocked_by import compute_blocked_by
from curriculum.graph.builder import build_graph_from_rules
from curriculum.graph.graph import CurriculumGraph
from curriculum.graph.models import (
    BlockedByResult,
    BlockedReason,
    CycleResult,
    DependencyChainStep,
    DependencyType,
    ExplainablePath,
    GraphEdge,
    GraphNode,
    TraversalDirection,
)
from curriculum.graph.traversal import (
    CycleDetectedError,
    MaxDepthExceededError,
    MaxNodesExceededError,
    detect_cycles,
    get_downstream_dependents,
    get_explainable_paths,
    get_relevant_subgraph,
    get_upstream_dependencies,
    topological_sort,
)
from curriculum.graph.visualizer import (
    generate_accessible_text_alternative,
    generate_subgraph_svg,
    generate_visualization_payload,
)

__all__ = [
    "BlockedByResult",
    "BlockedReason",
    "CurriculumGraph",
    "CycleDetectedError",
    "CycleResult",
    "DependencyChainStep",
    "DependencyType",
    "ExplainablePath",
    "GraphEdge",
    "GraphNode",
    "MaxDepthExceededError",
    "MaxNodesExceededError",
    "TraversalDirection",
    "build_graph_from_rules",
    "compute_blocked_by",
    "detect_cycles",
    "generate_accessible_text_alternative",
    "generate_subgraph_svg",
    "generate_visualization_payload",
    "get_downstream_dependents",
    "get_explainable_paths",
    "get_relevant_subgraph",
    "get_upstream_dependencies",
    "topological_sort",
]
