"""
Pure-Python Prerequisite Rule Engine (v1).
Independent of Django. Zero external dependencies.
"""

from rule_engine.core.context import (
    CompletedCourse,
    Exemption,
    RepeatedCoursePolicy,
    RuleContext,
    TransferCredit,
)
from rule_engine.core.interpreter import RuleInterpreter, evaluate_rule
from rule_engine.core.result import EvaluationResult, EvaluationStatus, NodeResult
from rule_engine.core.schema import (
    MAX_CONDITIONS,
    MAX_DEPTH,
    MAX_SIZE_BYTES,
    MAX_STRING_LENGTH,
    SCHEMA_VERSION,
)
from rule_engine.core.validator import (
    RuleValidationError,
    RuleValidator,
    validate_rule,
    validate_rule_strict,
)

__all__ = [
    "evaluate_rule",
    "validate_rule",
    "validate_rule_strict",
    "RuleInterpreter",
    "RuleValidator",
    "RuleValidationError",
    "RuleContext",
    "CompletedCourse",
    "TransferCredit",
    "Exemption",
    "RepeatedCoursePolicy",
    "EvaluationResult",
    "NodeResult",
    "EvaluationStatus",
    "SCHEMA_VERSION",
    "MAX_DEPTH",
    "MAX_CONDITIONS",
    "MAX_SIZE_BYTES",
    "MAX_STRING_LENGTH",
]
