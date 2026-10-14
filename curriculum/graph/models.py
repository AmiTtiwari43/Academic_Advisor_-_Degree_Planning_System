"""
Pure-Python Models and Dataclasses for Curriculum Dependency Graph.
Strictly decoupled from Django. Zero Django imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DependencyType(str, Enum):
    """Types of dependencies between courses."""

    PREREQUISITE = "prerequisite"
    COREQUISITE = "corequisite"
    ANTI_REQUISITE = "anti_requisite"


class TraversalDirection(str, Enum):
    """Direction for dependency graph traversal."""

    UPSTREAM = "upstream"      # Finding prerequisites / requirements of a course
    DOWNSTREAM = "downstream"  # Finding unlocks / dependents of a course


@dataclass(frozen=True)
class GraphNode:
    """Represents a course node within the curriculum graph."""

    code: str
    title: str = ""
    credits: float = 0.0
    is_offered: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "code", self.code.strip().upper())


@dataclass(frozen=True)
class GraphEdge:
    """
    Represents a directed dependency edge.
    By convention:
    `dependent` requires `prerequisite` via `dependency_type`.
    """

    dependent: str          # The course requiring the dependency (e.g. CS201)
    prerequisite: str       # The required course (e.g. CS101)
    dependency_type: DependencyType = DependencyType.PREREQUISITE
    min_grade: str | None = None
    group_type: str = "all_of"  # "all_of" or "any_of"
    group_id: str | None = None  # To distinguish alternative OR branches
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "dependent", self.dependent.strip().upper())
        object.__setattr__(self, "prerequisite", self.prerequisite.strip().upper())


@dataclass
class CycleResult:
    """Cycle detection analysis outcome."""

    has_cycle: bool
    cycles: list[list[str]] = field(default_factory=list)
    primary_cycle: list[str] | None = None

    @property
    def cycle_path_str(self) -> str:
        if not self.primary_cycle:
            return ""
        return " -> ".join(self.primary_cycle)


@dataclass
class DependencyChainStep:
    """A single step in an explainable dependency path."""

    course_code: str
    course_title: str
    dependency_type: DependencyType
    min_grade: str | None = None
    depth: int = 0


@dataclass
class ExplainablePath:
    """A full explanatory path from a target course back to root prerequisites."""

    target_course: str
    root_prerequisite: str
    path: list[str]
    steps: list[DependencyChainStep]
    explanation: str


@dataclass
class BlockedReason:
    """Reason why a course cannot be taken by a student context."""

    course_code: str
    missing_prerequisite: str
    dependency_type: DependencyType
    required_min_grade: str | None = None
    student_status: str | None = None  # "not_attempted", "in_progress", "grade_too_low", etc.
    student_grade: str | None = None
    is_direct: bool = True
    blocking_chain: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class BlockedByResult:
    """Result of computing what blocks a student from taking a course."""

    course_code: str
    is_blocked: bool
    direct_blockers: list[BlockedReason] = field(default_factory=list)
    indirect_blockers: list[BlockedReason] = field(default_factory=list)
    all_blocking_courses: set[str] = field(default_factory=set)
    unlocked_courses: list[str] = field(default_factory=list)
