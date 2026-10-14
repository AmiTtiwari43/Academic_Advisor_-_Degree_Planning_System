"""
Pure-Python SVG Visualizer for Curriculum Dependency Graphs.
Generates responsive, semantic SVG with accessible text alternatives.
Zero Django imports.
"""

from __future__ import annotations

import html
from collections import deque

from curriculum.graph.graph import CurriculumGraph
from curriculum.graph.models import DependencyType, GraphNode


def generate_accessible_text_alternative(
    graph: CurriculumGraph,
    target_code: str | None = None,
) -> str:
    """
    Generates a structured, accessible text transcript of the dependency graph.
    Suitable for screen readers or text-only fallback display.
    """
    lines: list[str] = []
    target = target_code.strip().upper() if target_code else None

    if target:
        lines.append(f"Curriculum Dependency Subgraph centered on {target}:")
    else:
        lines.append("Curriculum Dependency Graph Overview:")

    nodes = sorted(list(graph.nodes.values()), key=lambda n: n.code)
    if not nodes:
        return "Empty graph with no courses."

    for node in nodes:
        is_target = " [FOCUSED TARGET]" if node.code == target else ""
        lines.append(f"\nCourse: {node.code} - {node.title} ({node.credits} credits){is_target}")

        prereqs = graph.get_prerequisite_edges(node.code)
        if prereqs:
            lines.append("  Prerequisites required before taking this course:")
            for p in prereqs:
                grade_info = f", min grade {p.min_grade}" if p.min_grade else ""
                lines.append(f"    - {p.prerequisite} ({p.dependency_type.value}{grade_info})")
        else:
            lines.append("  Prerequisites: None (Foundational introductory course)")

        unlocks = graph.get_unlock_edges(node.code)
        if unlocks:
            lines.append("  Unlocks (courses requiring this):")
            for u in unlocks:
                lines.append(f"    - {u.dependent} ({u.dependency_type.value})")
        else:
            lines.append("  Unlocks: None (Terminal elective or capstone)")

    return "\n".join(lines)


def generate_subgraph_svg(
    graph: CurriculumGraph,
    target_code: str | None = None,
    width: int = 900,
    height: int = 500,
) -> str:
    """
    Renders the CurriculumGraph into a clean, modern SVG string.
    Includes accessible attributes (role="img", aria-labelledby, <title>, <desc>).
    """
    target = target_code.strip().upper() if target_code else None
    nodes = list(graph.nodes.values())

    if not nodes:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" aria-label="Empty Graph">'
            f'<rect width="100%" height="100%" fill="#0f172a"/>'
            f'<text x="50%" y="50%" text-anchor="middle" fill="#94a3b8" font-family="sans-serif" font-size="16">'
            f'No dependency graph nodes found.</text></svg>'
        )

    # 1. Compute layer depths using BFS
    # Prerequisites at top (lower rank/y), target in middle, dependents below
    ranks: dict[str, int] = {}
    if target and graph.has_node(target):
        ranks[target] = 2  # target baseline rank
        # Upstream (prerequisites) rank lower: 1, 0
        queue: deque[tuple[str, int]] = deque([(target, 2)])
        visited_up: set[str] = {target}
        while queue:
            curr, r = queue.popleft()
            for edge in graph.get_prerequisite_edges(curr):
                p = edge.prerequisite
                if p not in visited_up:
                    visited_up.add(p)
                    ranks[p] = max(0, r - 1)
                    queue.append((p, max(0, r - 1)))

        # Downstream (unlocks) rank higher: 3, 4
        queue_down: deque[tuple[str, int]] = deque([(target, 2)])
        visited_down: set[str] = {target}
        while queue_down:
            curr, r = queue_down.popleft()
            for edge in graph.get_unlock_edges(curr):
                d = edge.dependent
                if d not in visited_down:
                    visited_down.add(d)
                    ranks[d] = r + 1
                    queue_down.append((d, r + 1))
    else:
        # Generic rank based on number of prerequisites
        for node in nodes:
            ranks[node.code] = len(graph.get_prerequisite_edges(node.code))

    # Group nodes by rank
    layers: dict[int, list[GraphNode]] = {}
    for node in nodes:
        r = ranks.get(node.code, 1)
        if r not in layers:
            layers[r] = []
        layers[r].append(node)

    sorted_ranks = sorted(layers.keys())
    total_layers = len(sorted_ranks)

    # Node dimensions
    node_w = 170
    node_h = 60
    padding_y = 60
    available_h = max(height - 2 * padding_y, total_layers * 90)
    actual_svg_h = available_h + 2 * padding_y

    # Calculate coordinates for each node
    coords: dict[str, tuple[float, float]] = {}
    for layer_idx, rank in enumerate(sorted_ranks):
        layer_nodes = sorted(layers[rank], key=lambda n: n.code)
        num_in_layer = len(layer_nodes)
        y = padding_y + (layer_idx * (available_h / max(1, total_layers - 1))) if total_layers > 1 else actual_svg_h / 2

        layer_w = width - 100
        for node_idx, node in enumerate(layer_nodes):
            x = 50 + (node_idx + 0.5) * (layer_w / num_in_layer)
            coords[node.code] = (x, y)

    # SVG Building
    title_text = f"Curriculum Dependency Subgraph for {target}" if target else "Curriculum Dependency Subgraph"
    desc_text = f"Visual graph containing {len(nodes)} courses and {graph.edge_count} dependency connections."

    svg_parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {actual_svg_h}" '
        f'width="100%" height="100%" style="background:#090d16;border-radius:12px;font-family:Inter,system-ui,sans-serif;" '
        f'role="img" aria-labelledby="svg-title svg-desc">',
        f'<title id="svg-title">{html.escape(title_text)}</title>',
        f'<desc id="svg-desc">{html.escape(desc_text)}</desc>',
        '<defs>',
        '  <marker id="arrow-prereq" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8"/>',
        '  </marker>',
        '  <marker id="arrow-coreq" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#2dd4bf"/>',
        '  </marker>',
        '  <marker id="arrow-anti" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '    <path d="M 0 0 L 10 5 L 0 10 z" fill="#f87171"/>',
        '  </marker>',
        '  <linearGradient id="target-grad" x1="0%" y1="0%" x2="100%" y2="100%">',
        '    <stop offset="0%" stop-color="#4f46e5"/>',
        '    <stop offset="100%" stop-color="#7c3aed"/>',
        '  </linearGradient>',
        '  <linearGradient id="node-grad" x1="0%" y1="0%" x2="100%" y2="100%">',
        '    <stop offset="0%" stop-color="#1e293b"/>',
        '    <stop offset="100%" stop-color="#0f172a"/>',
        '  </linearGradient>',
        '</defs>',
    ]

    # Draw Edges first so nodes sit on top
    for edge in graph.get_all_edges():
        src = edge.dependent
        dst = edge.prerequisite
        if src in coords and dst in coords:
            x1, y1 = coords[src]
            x2, y2 = coords[dst]

            color = "#38bdf8"
            marker = "arrow-prereq"
            dash = ""
            if edge.dependency_type == DependencyType.COREQUISITE:
                color = "#2dd4bf"
                marker = "arrow-coreq"
                dash = 'stroke-dasharray="4,4"'
            elif edge.dependency_type == DependencyType.ANTI_REQUISITE:
                color = "#f87171"
                marker = "arrow-anti"
                dash = 'stroke-dasharray="2,2"'

            # Quadratic Bezier curve
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            svg_parts.append(
                f'<path d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" stroke="{color}" stroke-width="2" '
                f'fill="none" {dash} marker-end="url(#{marker})" opacity="0.8"/>'
            )

    # Draw Nodes
    for node in nodes:
        if node.code not in coords:
            continue
        cx, cy = coords[node.code]
        rx = cx - (node_w / 2)
        ry = cy - (node_h / 2)
        is_target = node.code == target

        fill = "url(#target-grad)" if is_target else "url(#node-grad)"
        stroke = "#a5b4fc" if is_target else "#334155"
        stroke_w = "2.5" if is_target else "1.5"

        truncated_title = (node.title[:18] + "…") if len(node.title) > 19 else node.title

        svg_parts.append(f'<g class="graph-node" tabindex="0" role="button" aria-label="Course {node.code}: {node.title}">')
        svg_parts.append(
            f'  <rect x="{rx}" y="{ry}" width="{node_w}" height="{node_h}" rx="8" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>'
        )
        # Course Code
        svg_parts.append(
            f'  <text x="{cx}" y="{ry + 24}" text-anchor="middle" fill="#ffffff" '
            f'font-size="14" font-weight="700">{html.escape(node.code)}</text>'
        )
        # Course Title / Credits
        svg_parts.append(
            f'  <text x="{cx}" y="{ry + 44}" text-anchor="middle" fill="#94a3b8" '
            f'font-size="11">{html.escape(truncated_title)} ({node.credits} cr)</text>'
        )
        svg_parts.append('</g>')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def generate_visualization_payload(
    graph: CurriculumGraph,
    target_code: str | None = None,
) -> dict[str, str]:
    """Generates both the SVG visual and the accessible text transcript."""
    return {
        "svg": generate_subgraph_svg(graph, target_code),
        "accessible_text": generate_accessible_text_alternative(graph, target_code),
    }
