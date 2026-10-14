"""
Data structures and domain models for the constraint-based plan optimizer.
Pure Python. Decoupled from Django ORM queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OptimizerCourse:
    """Represents a course to be scheduled by the optimizer."""

    code: str
    title: str = ""
    credits: float = 3.0
    is_mandatory: bool = True
    prerequisites: list[str] = field(default_factory=list)
    corequisites: list[str] = field(default_factory=list)
    anti_requisites: list[str] = field(default_factory=list)
    offered_seasons: list[str] = field(default_factory=lambda: ["FALL", "SPRING", "SUMMER"])
    preference_weight: int = 0  # Higher = preferred to schedule earlier
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.code = self.code.strip().upper()
        self.prerequisites = [p.strip().upper() for p in self.prerequisites]
        self.corequisites = [c.strip().upper() for c in self.corequisites]
        self.anti_requisites = [a.strip().upper() for a in self.anti_requisites]
        self.offered_seasons = [s.strip().upper() for s in self.offered_seasons]


@dataclass
class OptimizerTerm:
    """Represents an academic term period available for scheduling."""

    index: int
    code: str
    name: str = ""
    season: str = "FALL"
    year: int = 2026
    min_credits: float = 12.0
    max_credits: float = 18.0

    def __post_init__(self):
        self.code = self.code.strip().upper()
        self.season = self.season.strip().upper()


@dataclass
class ScheduledCourse:
    """Represents an assignment of a course to a term."""

    course_code: str
    term_index: int
    term_code: str
    credits: float


@dataclass
class TradeOffSummary:
    """Quantifies workload balance, pacing, and trade-offs for a plan."""

    plan_label: str
    total_terms_used: int
    graduation_term_code: str
    total_credits: float
    average_credits_per_term: float
    workload_variance: float
    max_term_credits: float
    min_term_credits: float
    trade_off_explanation: str


@dataclass
class CandidatePlan:
    """A feasible candidate multi-semester degree plan."""

    plan_index: int
    plan_label: str
    scheduled_courses: list[ScheduledCourse]
    terms_used: list[str]
    term_loads: dict[str, float]
    trade_offs: TradeOffSummary
    is_validated: bool = False
    validation_notes: list[str] = field(default_factory=list)


@dataclass
class OptimizationRequest:
    """Input payload for plan optimization."""

    available_terms: list[OptimizerTerm]
    courses_to_schedule: list[OptimizerCourse]
    completed_courses: set[str] = field(default_factory=set)
    in_progress_courses: set[str] = field(default_factory=set)
    target_credits_per_term: float = 15.0
    enforce_min_credits: bool = True
    max_plans: int = 3
    timeout_seconds: float = 5.0

    def __post_init__(self):
        self.completed_courses = {c.strip().upper() for c in self.completed_courses}
        self.in_progress_courses = {c.strip().upper() for c in self.in_progress_courses}


@dataclass
class OptimizationResult:
    """Overall outcome of the optimization solve."""

    is_feasible: bool
    candidate_plans: list[CandidatePlan] = field(default_factory=list)
    blocking_constraints: list[str] = field(default_factory=list)
    solver_status: str = "UNKNOWN"
    solve_time_seconds: float = 0.0
