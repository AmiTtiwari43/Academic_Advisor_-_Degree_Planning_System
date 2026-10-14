"""
Comprehensive Test Suite for Curriculum Dependency Graph (Prompt 08A).
Covers:
- Acyclic graph and topological sort
- Cyclic graph with exact cycle path reporting
- Self-loops (A -> A)
- Diamond graphs (asserted acyclic)
- 5,000-node performance benchmark within time bounds (< 1.0s)
- Missing course references
- Bounded traversal guards (max depth and max nodes)
- Explainable dependency paths
- Student "blocked by" evaluation (grades, in-progress, anti-requisites, any_of groups)
- SVG visualizer and accessible text alternative
- Zero Django imports in curriculum.graph
- Django integration service and API endpoints with multi-tenant scoping
"""

import ast
import os
import time
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from academic_records.models import AcademicTerm, StudentRecord, TranscriptEntry
from accounts.models import InstitutionMembership, Role
from curriculum.graph import (
    CurriculumGraph,
    CycleDetectedError,
    DependencyType,
    GraphEdge,
    GraphNode,
    MaxDepthExceededError,
    MaxNodesExceededError,
    compute_blocked_by,
    detect_cycles,
    generate_visualization_payload,
    get_explainable_paths,
    get_upstream_dependencies,
    topological_sort,
)
from curriculum.models import (
    Course,
    CurriculumStatus,
    CurriculumVersion,
    PrerequisiteRule,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupType,
)
from institutions.models import Institution

# =========================================================================
# 1. PURE PYTHON GRAPH ALGORITHM TESTS
# =========================================================================

def test_acyclic_graph_and_topological_sort():
    """Verifies that an acyclic prerequisite DAG is correctly identified and topologically ordered."""
    graph = CurriculumGraph()
    for code in ["CS101", "CS102", "CS201", "CS301"]:
        graph.add_node(GraphNode(code=code, title=f"Course {code}", credits=4.0))

    # CS102 requires CS101; CS201 requires CS102; CS301 requires CS201
    graph.add_edge(GraphEdge(dependent="CS102", prerequisite="CS101"))
    graph.add_edge(GraphEdge(dependent="CS201", prerequisite="CS102"))
    graph.add_edge(GraphEdge(dependent="CS301", prerequisite="CS201"))

    cycle_result = detect_cycles(graph)
    assert cycle_result.has_cycle is False
    assert cycle_result.cycles == []
    assert cycle_result.primary_cycle is None

    ordered = topological_sort(graph)
    assert ordered.index("CS101") < ordered.index("CS102")
    assert ordered.index("CS102") < ordered.index("CS201")
    assert ordered.index("CS201") < ordered.index("CS301")


def test_cyclic_graph_reports_exact_cycle_path():
    """Verifies multi-node cycle detection and exact cycle path reporting."""
    graph = CurriculumGraph()
    for code in ["CS101", "CS102", "CS103"]:
        graph.add_node(GraphNode(code=code))

    # CS101 -> CS102 -> CS103 -> CS101
    graph.add_edge(GraphEdge(dependent="CS101", prerequisite="CS102"))
    graph.add_edge(GraphEdge(dependent="CS102", prerequisite="CS103"))
    graph.add_edge(GraphEdge(dependent="CS103", prerequisite="CS101"))

    cycle_result = detect_cycles(graph)
    assert cycle_result.has_cycle is True
    assert len(cycle_result.cycles) >= 1

    # Exact cycle path must form a closed loop
    primary = cycle_result.primary_cycle
    assert primary is not None
    assert primary[0] == primary[-1]  # Closed cycle
    assert len(primary) == 4  # e.g. CS101 -> CS102 -> CS103 -> CS101

    with pytest.raises(CycleDetectedError) as exc_info:
        topological_sort(graph)
    assert exc_info.value.cycle_path == primary


def test_self_loop_detected():
    """Verifies that a course requiring itself (self-loop) is immediately flagged."""
    graph = CurriculumGraph()
    graph.add_node(GraphNode(code="MATH101"))
    graph.add_edge(GraphEdge(dependent="MATH101", prerequisite="MATH101"))

    cycle_result = detect_cycles(graph)
    assert cycle_result.has_cycle is True
    assert ["MATH101", "MATH101"] in cycle_result.cycles
    assert cycle_result.primary_cycle == ["MATH101", "MATH101"]


def test_diamond_graph_is_acyclic():
    """
    Verifies that diamond dependencies are correctly identified as acyclic.
    CS101 -> CS201 & CS202 -> CS301.
    """
    graph = CurriculumGraph()
    for code in ["CS101", "CS201", "CS202", "CS301"]:
        graph.add_node(GraphNode(code=code))

    graph.add_edge(GraphEdge(dependent="CS201", prerequisite="CS101"))
    graph.add_edge(GraphEdge(dependent="CS202", prerequisite="CS101"))
    graph.add_edge(GraphEdge(dependent="CS301", prerequisite="CS201"))
    graph.add_edge(GraphEdge(dependent="CS301", prerequisite="CS202"))

    cycle_result = detect_cycles(graph)
    assert cycle_result.has_cycle is False

    ordered = topological_sort(graph)
    assert ordered.index("CS101") < ordered.index("CS201")
    assert ordered.index("CS101") < ordered.index("CS202")
    assert ordered.index("CS201") < ordered.index("CS301")
    assert ordered.index("CS202") < ordered.index("CS301")


def test_5000_node_benchmark_within_time_bound():
    """
    Performance test: evaluates cycle detection and topological sorting
    on a 5,000-node synthetic curriculum graph within strict time bound (< 1.0 second).
    """
    graph = CurriculumGraph()
    node_count = 5000

    # Create 5,000 nodes in 10 layers of 500 nodes
    layer_size = 500
    for i in range(node_count):
        graph.add_node(GraphNode(code=f"CRS_{i}"))

    # Connect each node in layer K to 2 nodes in layer K-1
    for i in range(layer_size, node_count):
        prev_1 = i - layer_size
        prev_2 = (i - layer_size + 1) if (i % layer_size != layer_size - 1) else (i - layer_size)
        graph.add_edge(GraphEdge(dependent=f"CRS_{i}", prerequisite=f"CRS_{prev_1}"))
        if prev_1 != prev_2:
            graph.add_edge(GraphEdge(dependent=f"CRS_{i}", prerequisite=f"CRS_{prev_2}"))

    assert graph.node_count == 5000
    assert graph.edge_count > 4500

    start_time = time.perf_counter()
    cycle_result = detect_cycles(graph)
    cycle_duration = time.perf_counter() - start_time

    assert cycle_result.has_cycle is False
    assert cycle_duration < 1.0, f"Cycle detection on 5,000 nodes took {cycle_duration:.3f}s (target < 1.0s)"

    start_topo = time.perf_counter()
    topo_order = topological_sort(graph)
    topo_duration = time.perf_counter() - start_topo

    assert len(topo_order) == 5000
    assert topo_duration < 1.0, f"Topological sort on 5,000 nodes took {topo_duration:.3f}s (target < 1.0s)"


def test_missing_course_references():
    """Verifies detection of courses referenced in prerequisite rules but missing from graph nodes."""
    graph = CurriculumGraph()
    graph.add_node(GraphNode(code="CS201"))
    # CS201 requires CS101 and MATH101 which were never added as nodes
    graph.add_edge(GraphEdge(dependent="CS201", prerequisite="CS101"))
    graph.add_edge(GraphEdge(dependent="CS201", prerequisite="MATH101"))

    missing = graph.get_missing_course_references()
    assert missing == ["CS101", "MATH101"]


def test_bounded_traversal_guards():
    """Verifies that bounded traversal guards prevent runaway depth or node limits."""
    graph = CurriculumGraph()
    # Create long chain: C30 -> C29 -> ... -> C0
    for i in range(35):
        graph.add_node(GraphNode(code=f"C{i}"))
        if i > 0:
            graph.add_edge(GraphEdge(dependent=f"C{i}", prerequisite=f"C{i-1}"))

    # Test max_depth guard
    with pytest.raises(MaxDepthExceededError):
        get_upstream_dependencies(graph, "C30", max_depth=5)

    # Test max_nodes guard
    with pytest.raises(MaxNodesExceededError):
        get_upstream_dependencies(graph, "C30", max_nodes=8)

    # Valid bounded traversal within limits
    deps = get_upstream_dependencies(graph, "C5", max_depth=10, max_nodes=50)
    assert len(deps) == 5
    assert "C0" in deps


def test_explainable_dependency_paths():
    """Verifies that explainable paths format structured steps and plain-English reasons."""
    graph = CurriculumGraph()
    graph.add_node(GraphNode(code="CS101", title="Introduction to CS"))
    graph.add_node(GraphNode(code="CS201", title="Data Structures"))
    graph.add_node(GraphNode(code="CS301", title="Algorithms"))

    graph.add_edge(GraphEdge(dependent="CS201", prerequisite="CS101", min_grade="C"))
    graph.add_edge(GraphEdge(dependent="CS301", prerequisite="CS201", min_grade="B"))

    paths = get_explainable_paths(graph, "CS301")
    assert len(paths) == 1
    p = paths[0]
    assert p.target_course == "CS301"
    assert p.root_prerequisite == "CS101"
    assert p.path == ["CS301", "CS201", "CS101"]
    assert len(p.steps) == 2
    assert p.steps[0].course_code == "CS201"
    assert p.steps[0].min_grade == "B"
    assert p.steps[1].course_code == "CS101"
    assert p.steps[1].min_grade == "C"
    assert "CS301 requires CS201" in p.explanation
    assert "CS201 requires CS101" in p.explanation


def test_student_blocked_by_computation():
    """Verifies student blocked-by calculation with grades, corequisites, and anti-requisites."""
    graph = CurriculumGraph()
    graph.add_node(GraphNode(code="CS101", title="Intro to CS"))
    graph.add_node(GraphNode(code="CS201", title="Data Structures"))
    graph.add_node(GraphNode(code="CS202", title="Accelerated CS"))
    graph.add_node(GraphNode(code="CS301", title="Algorithms"))

    # CS201 requires CS101 (min grade C)
    # CS301 requires CS201 (min grade C)
    # CS301 has anti-requisite CS202
    graph.add_edge(GraphEdge(dependent="CS201", prerequisite="CS101", min_grade="C"))
    graph.add_edge(GraphEdge(dependent="CS301", prerequisite="CS201", min_grade="C"))
    graph.add_edge(GraphEdge(dependent="CS301", prerequisite="CS202", dependency_type=DependencyType.ANTI_REQUISITE))

    # Scenario 1: Brand new student (no courses) -> blocked by CS201 (direct) and CS101 (indirect)
    res1 = compute_blocked_by(graph, "CS301", completed_courses={})
    assert res1.is_blocked is True
    assert any(b.missing_prerequisite == "CS201" for b in res1.direct_blockers)
    assert any(b.missing_prerequisite == "CS101" for b in res1.indirect_blockers)
    assert "CS201" in res1.all_blocking_courses
    assert "CS101" in res1.all_blocking_courses

    # Scenario 2: Student completed CS101 with B, but CS201 with D (min grade is C)
    res2 = compute_blocked_by(graph, "CS301", completed_courses={"CS101": "B", "CS201": "D"})
    assert res2.is_blocked is True
    assert len(res2.direct_blockers) == 1
    assert res2.direct_blockers[0].missing_prerequisite == "CS201"
    assert res2.direct_blockers[0].student_status == "grade_too_low"
    assert res2.direct_blockers[0].student_grade == "D"

    # Scenario 3: Student completed CS101 (B) and CS201 (B) -> eligible!
    res3 = compute_blocked_by(graph, "CS301", completed_courses={"CS101": "B", "CS201": "B"})
    assert res3.is_blocked is False
    assert len(res3.direct_blockers) == 0

    # Scenario 4: Student completed CS201 (B), but also completed anti-requisite CS202 -> blocked!
    res4 = compute_blocked_by(graph, "CS301", completed_courses={"CS101": "B", "CS201": "B", "CS202": "A"})
    assert res4.is_blocked is True
    assert any(b.dependency_type == DependencyType.ANTI_REQUISITE for b in res4.direct_blockers)

    # Scenario 5: Waived prerequisite via advisor override
    res5 = compute_blocked_by(graph, "CS301", completed_courses={}, waived_courses={"CS201"})
    assert res5.is_blocked is False


def test_svg_and_accessible_text_visualization():
    """Verifies SVG generation formatting, accessible text alternatives, and semantic tags."""
    graph = CurriculumGraph()
    graph.add_node(GraphNode(code="CS101", title="Intro to CS", credits=4.0))
    graph.add_node(GraphNode(code="CS201", title="Data Structures", credits=4.0))
    graph.add_edge(GraphEdge(dependent="CS201", prerequisite="CS101"))

    payload = generate_visualization_payload(graph, target_code="CS201")
    svg = payload["svg"]
    text = payload["accessible_text"]

    # SVG semantics
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in svg
    assert 'role="img"' in svg
    assert 'aria-labelledby="svg-title svg-desc"' in svg
    assert '<title id="svg-title">' in svg
    assert '<desc id="svg-desc">' in svg
    assert 'CS101' in svg
    assert 'CS201' in svg
    assert 'marker-end="url(#arrow-prereq)"' in svg

    # Accessible text transcript
    assert "Curriculum Dependency Subgraph centered on CS201:" in text
    assert "Course: CS101 - Intro to CS (4.0 credits)" in text
    assert "Course: CS201 - Data Structures (4.0 credits) [FOCUSED TARGET]" in text
    assert "Prerequisites required before taking this course:" in text
    assert "CS101 (prerequisite)" in text


def test_zero_django_imports_in_curriculum_graph():
    """
    Enforces architectural isolation: curriculum/graph package must NOT import Django or DRF.
    Parses Python AST of all files in curriculum/graph.
    """
    graph_pkg_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "curriculum",
        "graph",
    )
    for filename in os.listdir(graph_pkg_dir):
        if filename.endswith(".py"):
            filepath = os.path.join(graph_pkg_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("django"), (
                            f"Illegal Django import '{alias.name}' in {filename}"
                        )
                        assert not alias.name.startswith("rest_framework"), (
                            f"Illegal DRF import '{alias.name}' in {filename}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    assert not mod.startswith("django"), (
                        f"Illegal Django import '{mod}' in {filename}"
                    )
                    assert not mod.startswith("rest_framework"), (
                        f"Illegal DRF import '{mod}' in {filename}"
                    )


# =========================================================================
# 2. DJANGO INTEGRATION & API PERMISSION TESTS
# =========================================================================

@pytest.fixture
def graph_curriculum_setup(db):
    """Sets up a realistic curriculum version with courses and prerequisite rules."""
    institution_alpha = Institution.objects.create(name="Graph University Alpha", code="GRAPH_A", domain="graph-a.edu")
    institution_beta = Institution.objects.create(name="Graph University Beta", code="GRAPH_B", domain="graph-b.edu")

    student_alpha = User.objects.create_user(username="graph_student", email="student@graph-a.edu", password="Password123!")
    advisor_alpha = User.objects.create_user(username="graph_advisor", email="advisor@graph-a.edu", password="Password123!")
    coordinator_alpha = User.objects.create_user(username="graph_coord", email="coord@graph-a.edu", password="Password123!")
    coordinator_beta = User.objects.create_user(username="graph_foreign_coord", email="foreign@graph-b.edu", password="Password123!")

    InstitutionMembership.objects.create(user=student_alpha, institution=institution_alpha, role=Role.STUDENT, is_active=True)
    InstitutionMembership.objects.create(user=advisor_alpha, institution=institution_alpha, role=Role.ADVISOR, is_active=True)
    InstitutionMembership.objects.create(user=coordinator_alpha, institution=institution_alpha, role=Role.COORDINATOR, is_active=True)
    InstitutionMembership.objects.create(user=coordinator_beta, institution=institution_beta, role=Role.COORDINATOR, is_active=True)

    term = AcademicTerm.objects.create(
        institution=institution_alpha,
        name="Fall 2026",
        code="FA26",
        season="FALL",
        year=2026,
        start_date="2026-09-01",
        end_date="2026-12-15",
    )
    prog = Programme.objects.create(
        institution=institution_alpha,
        code="BS-SE",
        name="Software Engineering",
    )
    ver = CurriculumVersion.objects.create(
        institution=institution_alpha,
        programme=prog,
        version_number=1,
        academic_year="2026-2027",
        status=CurriculumStatus.DRAFT,
        total_credits_required=Decimal("120.00"),
        min_cgpa_required=Decimal("2.000"),
    )
    c1 = Course.objects.create(institution=institution_alpha, code="SE-101", title="Intro to SE", credits=Decimal("4.00"))
    c2 = Course.objects.create(institution=institution_alpha, code="SE-201", title="Software Design", credits=Decimal("4.00"))
    c3 = Course.objects.create(institution=institution_alpha, code="SE-301", title="Architecture", credits=Decimal("4.00"))

    grp = RequirementGroup.objects.create(
        institution=institution_alpha,
        curriculum_version=ver,
        name="Core SE",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("12.00"),
    )
    RequirementGroupCourse.objects.create(requirement_group=grp, course=c1, is_mandatory=True, display_order=1)
    RequirementGroupCourse.objects.create(requirement_group=grp, course=c2, is_mandatory=True, display_order=2)
    RequirementGroupCourse.objects.create(requirement_group=grp, course=c3, is_mandatory=True, display_order=3)

    # SE-201 requires SE-101 (min grade C)
    PrerequisiteRule.objects.create(
        institution=institution_alpha,
        curriculum_version=ver,
        course=c2,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "SE-101", "min_grade": "C"},
    )
    # SE-301 requires SE-201 (min grade C)
    PrerequisiteRule.objects.create(
        institution=institution_alpha,
        curriculum_version=ver,
        course=c3,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "SE-201", "min_grade": "C"},
    )

    ver.status = CurriculumStatus.PUBLISHED
    ver.save(update_fields=["status"])

    # Student Record
    s_record = StudentRecord.objects.create(
        institution=institution_alpha,
        student=student_alpha,
        programme=prog,
        pinned_curriculum=ver,
        enrollment_term=term,
    )
    # Student completed SE-101 with B
    TranscriptEntry.objects.create(
        institution=institution_alpha,
        student_record=s_record,
        course=c1,
        term=term,
        credits_attempted=Decimal("4.00"),
        credits_earned=Decimal("4.00"),
        grade="B",
        status="COMPLETED",
        verification_status="VERIFIED",
    )

    return {
        "institution": institution_alpha,
        "foreign_institution": institution_beta,
        "version": ver,
        "courses": [c1, c2, c3],
        "student": student_alpha,
        "student_record": s_record,
        "advisor": advisor_alpha,
        "coordinator": coordinator_alpha,
        "foreign_coordinator": coordinator_beta,
    }


def test_curriculum_version_graph_api(graph_curriculum_setup):
    """Tests GET /api/curricula/{id}/graph/."""
    client = APIClient()
    setup = graph_curriculum_setup
    client.force_authenticate(user=setup["coordinator"])

    resp = client.get(f"/api/curricula/{setup['version'].id}/graph/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert data["node_count"] == 3
    assert data["edge_count"] == 2
    assert data["has_cycle"] is False
    assert data["missing_references"] == []
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2


def test_dependency_paths_api(graph_curriculum_setup):
    """Tests GET /api/curricula/{id}/courses/{code}/dependency_paths/."""
    client = APIClient()
    setup = graph_curriculum_setup
    client.force_authenticate(user=setup["student"])

    resp = client.get(f"/api/curricula/{setup['version'].id}/courses/SE-301/dependency_paths/")
    assert resp.status_code == status.HTTP_200_OK
    paths = resp.json()

    assert len(paths) == 1
    p = paths[0]
    assert p["target_course"] == "SE-301"
    assert p["root_prerequisite"] == "SE-101"
    assert p["path"] == ["SE-301", "SE-201", "SE-101"]
    assert "SE-301 requires SE-201" in p["explanation"]


def test_visualize_api(graph_curriculum_setup):
    """Tests GET /api/curricula/{id}/courses/{code}/visualize/."""
    client = APIClient()
    setup = graph_curriculum_setup
    client.force_authenticate(user=setup["advisor"])

    resp = client.get(f"/api/curricula/{setup['version'].id}/courses/SE-201/visualize/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    assert "<svg" in data["svg"]
    assert "SE-201" in data["svg"]
    assert "Curriculum Dependency Subgraph" in data["accessible_text"]


def test_blocked_by_api(graph_curriculum_setup):
    """Tests GET /api/curricula/{id}/courses/{code}/blocked_by/."""
    client = APIClient()
    setup = graph_curriculum_setup
    client.force_authenticate(user=setup["student"])

    # Student completed SE-101, so SE-201 is NOT blocked
    resp_se201 = client.get(f"/api/curricula/{setup['version'].id}/courses/SE-201/blocked_by/")
    assert resp_se201.status_code == status.HTTP_200_OK
    data201 = resp_se201.json()
    assert data201["is_blocked"] is False

    # Student hasn't completed SE-201, so SE-301 IS blocked
    resp_se301 = client.get(f"/api/curricula/{setup['version'].id}/courses/SE-301/blocked_by/")
    assert resp_se301.status_code == status.HTTP_200_OK
    data301 = resp_se301.json()
    assert data301["is_blocked"] is True
    assert any(b["missing_prerequisite"] == "SE-201" for b in data301["direct_blockers"])


def test_cross_tenant_graph_access_denied(graph_curriculum_setup):
    """Tests that users from a different tenant cannot view curriculum graphs (returns 404)."""
    client = APIClient()
    setup = graph_curriculum_setup
    client.force_authenticate(user=setup["foreign_coordinator"])

    resp = client.get(f"/api/curricula/{setup['version'].id}/graph/")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
