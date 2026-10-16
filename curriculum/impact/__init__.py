"""
Curriculum Impact Package.
Exports impact domain models and data structures.
"""

from curriculum.impact.models import (
    CurriculumImpactReport,
    ImpactSeverity,
    ImpactSummary,
    PlanImpactDetail,
    PrerequisiteChange,
    RequirementDiff,
    StudentImpactDetail,
)

__all__ = [
    "CurriculumImpactReport",
    "ImpactSeverity",
    "ImpactSummary",
    "PlanImpactDetail",
    "PrerequisiteChange",
    "RequirementDiff",
    "StudentImpactDetail",
]
