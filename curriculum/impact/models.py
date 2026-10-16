"""
Domain models and data structures for Curriculum Change Impact Analyzer.
Pure Python. Decoupled from direct database mutations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ImpactSeverity(str, Enum):
    HIGH = "HIGH"          # Graduation delay or degree satisfaction lost
    MODERATE = "MODERATE"  # Newly unmet requirement or lost course eligibility
    LOW = "LOW"            # Elective changes or relaxed prerequisites
    NONE = "NONE"          # No negative impact


@dataclass
class RequirementDiff:
    """Represents a structural difference in a requirement group between versions."""

    group_id: str
    group_name: str
    change_type: str  # ADDED, REMOVED, MODIFIED, UNCHANGED
    old_min_credits: float | None = None
    new_min_credits: float | None = None
    old_min_courses: int | None = None
    new_min_courses: int | None = None
    added_mandatory_courses: list[str] = field(default_factory=list)
    removed_mandatory_courses: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PrerequisiteChange:
    """Represents a change in prerequisite rules for a course between versions."""

    course_code: str
    course_title: str
    change_type: str  # ADDED, REMOVED, STRENGTHENED, RELAXED, MODIFIED
    old_rule_summary: str = ""
    new_rule_summary: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StudentImpactDetail:
    """Impact analysis outcome for an individual student."""

    student_id: str
    student_username: str
    student_name: str
    severity: ImpactSeverity
    is_degree_satisfaction_lost: bool = False
    remaining_credits_increase: float = 0.0
    newly_unmet_groups: list[str] = field(default_factory=list)
    prerequisite_ineligibilities: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass
class PlanImpactDetail:
    """Impact analysis outcome for an individual degree plan."""

    plan_id: str
    plan_name: str
    student_username: str
    severity: ImpactSeverity
    graduation_delay_terms: int = 0
    old_projected_grad_term: str | None = None
    new_projected_grad_term: str | None = None
    new_hard_constraints_count: int = 0
    new_hard_constraint_messages: list[str] = field(default_factory=list)
    offering_conflicts_count: int = 0
    offering_conflict_messages: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass
class ImpactSummary:
    """High-level quantitative summary of the impact analysis."""

    total_students_assessed: int = 0
    total_students_affected: int = 0
    total_plans_assessed: int = 0
    total_plans_affected: int = 0
    students_delayed_count: int = 0
    high_impact_count: int = 0
    moderate_impact_count: int = 0
    low_impact_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CurriculumImpactReport:
    """Full comprehensive impact analysis report comparing draft vs published version."""

    draft_version_id: str
    draft_version_number: int
    published_version_id: str
    published_version_number: int
    programme_code: str
    programme_name: str
    summary: ImpactSummary
    requirement_changes: list[RequirementDiff] = field(default_factory=list)
    prerequisite_changes: list[PrerequisiteChange] = field(default_factory=list)
    affected_students: list[StudentImpactDetail] = field(default_factory=list)
    affected_plans: list[PlanImpactDetail] = field(default_factory=list)
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_version_id": self.draft_version_id,
            "draft_version_number": self.draft_version_number,
            "published_version_id": self.published_version_id,
            "published_version_number": self.published_version_number,
            "programme_code": self.programme_code,
            "programme_name": self.programme_name,
            "summary": self.summary.to_dict(),
            "requirement_changes": [rc.to_dict() for rc in self.requirement_changes],
            "prerequisite_changes": [pc.to_dict() for pc in self.prerequisite_changes],
            "affected_students": [s.to_dict() for s in self.affected_students],
            "affected_plans": [p.to_dict() for p in self.affected_plans],
            "analyzed_at": self.analyzed_at,
        }
