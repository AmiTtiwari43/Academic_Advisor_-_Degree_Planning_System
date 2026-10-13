"""
Evaluation Result Dataclasses & Status Enum (v1).
Pure Python.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EvaluationStatus(str, Enum):
    SATISFIED = "SATISFIED"
    UNSATISFIED = "UNSATISFIED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class NodeResult:
    node_path: str
    type: str
    status: EvaluationStatus
    explanation: str
    blocking_reasons: tuple[str, ...] = field(default_factory=tuple)
    children: tuple["NodeResult", ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "node_path": self.node_path,
            "type": self.type,
            "status": self.status.value,
            "explanation": self.explanation,
            "blocking_reasons": list(self.blocking_reasons),
            "children": [c.to_dict() for c in self.children],
        }


@dataclass(frozen=True)
class EvaluationResult:
    eligible: bool
    status: EvaluationStatus
    node_results: NodeResult
    blocking_reasons: tuple[str, ...]
    rule_id: Optional[str] = None
    curriculum_version_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "status": self.status.value,
            "rule_id": self.rule_id,
            "curriculum_version_id": self.curriculum_version_id,
            "blocking_reasons": list(self.blocking_reasons),
            "node_results": self.node_results.to_dict(),
        }
