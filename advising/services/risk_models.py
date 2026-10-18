from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SourceRecordReference:
    """
    Exact entity reference backing a transparent risk indicator.
    """
    entity_type: str
    record_id: str
    display_name: str

    def to_dict(self) -> dict[str, str]:
        return {
            "entity_type": self.entity_type,
            "record_id": self.record_id,
            "display_name": self.display_name,
        }


@dataclass
class RiskIndicator:
    """
    A single deterministic, rule-based academic risk indicator.
    Contains zero machine learning; fully explained by contributing factors and source records.
    """
    code: str
    name: str
    severity: str  # CRITICAL, WARNING, INFO
    category: str  # PREREQUISITE, COURSE_OFFERING, TIMELINE_COMPLETION, REGISTRATION, ACADEMIC_STANDING
    message: str
    contributing_factors: dict[str, Any] = field(default_factory=dict)
    source_records: list[dict[str, str]] = field(default_factory=list)
    actionable_recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "contributing_factors": self.contributing_factors,
            "source_records": self.source_records,
            "actionable_recommendation": self.actionable_recommendation,
        }


@dataclass
class RiskEvaluationResult:
    """
    Complete academic risk assessment for a student.
    """
    student_id: str
    student_username: str
    institution_id: str
    overall_risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    active_risk_count: int
    critical_risk_count: int
    warning_risk_count: int
    info_risk_count: int
    indicators: list[RiskIndicator] = field(default_factory=list)
    assessed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "student_id": self.student_id,
            "student_username": self.student_username,
            "institution_id": self.institution_id,
            "overall_risk_level": self.overall_risk_level,
            "active_risk_count": self.active_risk_count,
            "critical_risk_count": self.critical_risk_count,
            "warning_risk_count": self.warning_risk_count,
            "info_risk_count": self.info_risk_count,
            "indicators": [ind.to_dict() for ind in self.indicators],
            "assessed_at": self.assessed_at,
            "summary": self.summary,
        }
