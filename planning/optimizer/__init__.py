"""
Planning Optimizer package.
Pure Python constraint-based degree plan optimizer powered by Google OR-Tools CP-SAT.
"""

from planning.optimizer.infeasibility import diagnose_infeasibility
from planning.optimizer.models import (
    CandidatePlan,
    OptimizationRequest,
    OptimizationResult,
    OptimizerCourse,
    OptimizerTerm,
    ScheduledCourse,
    TradeOffSummary,
)
from planning.optimizer.solver import optimize_degree_plan

__all__ = [
    "CandidatePlan",
    "OptimizationRequest",
    "OptimizationResult",
    "OptimizerCourse",
    "OptimizerTerm",
    "ScheduledCourse",
    "TradeOffSummary",
    "diagnose_infeasibility",
    "optimize_degree_plan",
]
