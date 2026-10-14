"""
Curriculum Validation Service.
Performs pre-publication validation including cycle detection, credit balance audits,
rule AST schema validation, and prerequisite dependency graph verification.
"""

from dataclasses import dataclass, field
from typing import Any

from curriculum.models import CurriculumVersion
from rule_engine.core import RuleValidationError, validate_rule_strict


@dataclass
class ValidationErrorDetail:
    code: str
    message: str
    entity_type: str = "curriculum"
    entity_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationWarningDetail:
    code: str
    message: str
    entity_type: str = "curriculum"
    entity_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    is_valid: bool
    errors: list[ValidationErrorDetail] = field(default_factory=list)
    warnings: list[ValidationWarningDetail] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "entity_type": e.entity_type,
                    "entity_id": e.entity_id,
                    "details": e.details,
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "code": w.code,
                    "message": w.message,
                    "entity_type": w.entity_type,
                    "entity_id": w.entity_id,
                    "details": w.details,
                }
                for w in self.warnings
            ],
        }


def _extract_referenced_courses(node: Any) -> set[str]:
    """Recursively extracts all course codes mentioned in a rule AST."""
    courses: set[str] = set()
    if not isinstance(node, dict):
        return courses

    op_type = node.get("type")
    if op_type in ("course_completed", "corequisite", "anti_requisite"):
        code = node.get("course_code")
        if isinstance(code, str) and code.strip():
            courses.add(code.strip().upper())

    if "conditions" in node and isinstance(node["conditions"], list):
        for child in node["conditions"]:
            courses.update(_extract_referenced_courses(child))

    return courses


def validate_curriculum_version(version: CurriculumVersion) -> ValidationReport:
    """
    Validates a curriculum version for structural integrity, credit balance,
    DAG acyclicity, and prerequisite correctness.
    """
    errors: list[ValidationErrorDetail] = []
    warnings: list[ValidationWarningDetail] = []

    # 1. Version Thresholds
    if version.total_credits_required <= 0:
        errors.append(
            ValidationErrorDetail(
                code="INVALID_CREDITS_THRESHOLD",
                message=f"Total required credits must be positive, got {version.total_credits_required}.",
                entity_type="CurriculumVersion",
                entity_id=str(version.id),
            )
        )
    if version.min_cgpa_required < 0 or version.min_cgpa_required > 4.0:
        errors.append(
            ValidationErrorDetail(
                code="INVALID_CGPA_THRESHOLD",
                message=f"Minimum required CGPA must be between 0.0 and 4.0, got {version.min_cgpa_required}.",
                entity_type="CurriculumVersion",
                entity_id=str(version.id),
            )
        )

    # 2. Requirement Groups & Hierarchy
    groups = list(
        version.requirement_groups.prefetch_related("group_courses__course", "children").all()
    )
    if not groups:
        errors.append(
            ValidationErrorDetail(
                code="NO_REQUIREMENT_GROUPS",
                message="Curriculum version must define at least one requirement group.",
                entity_type="CurriculumVersion",
                entity_id=str(version.id),
            )
        )

    # Check for cycles in requirement group parent hierarchy
    parent_map: dict[str, str | None] = {
        str(g.id): str(g.parent_id) if g.parent_id else None for g in groups
    }
    for g in groups:
        visited: set[str] = set()
        curr: str | None = str(g.id)
        while curr is not None:
            if curr in visited:
                errors.append(
                    ValidationErrorDetail(
                        code="CYCLIC_REQUIREMENT_GROUP",
                        message=f"Cyclic requirement group hierarchy detected involving group '{g.name}'.",
                        entity_type="RequirementGroup",
                        entity_id=str(g.id),
                    )
                )
                break
            visited.add(curr)
            curr = parent_map.get(curr)

    # Check credit availability per group
    for g in groups:
        if g.min_credits < 0:
            errors.append(
                ValidationErrorDetail(
                    code="NEGATIVE_GROUP_CREDITS",
                    message=f"Requirement group '{g.name}' cannot have negative min_credits ({g.min_credits}).",
                    entity_type="RequirementGroup",
                    entity_id=str(g.id),
                )
            )

        # Calculate available credits in directly attached courses
        attached_courses = [gc.course for gc in g.group_courses.all()]
        available_credits = sum(c.credits for c in attached_courses if c.is_active)
        if not g.children.exists() and g.min_credits > available_credits:
            errors.append(
                ValidationErrorDetail(
                    code="INSUFFICIENT_AVAILABLE_CREDITS",
                    message=(
                        f"Requirement group '{g.name}' requires {g.min_credits} credits, "
                        f"but only {available_credits} credits are available in assigned courses."
                    ),
                    entity_type="RequirementGroup",
                    entity_id=str(g.id),
                    details={
                        "min_credits": float(g.min_credits),
                        "available_credits": float(available_credits),
                    },
                )
            )

        if not attached_courses and not g.children.exists():
            warnings.append(
                ValidationWarningDetail(
                    code="EMPTY_REQUIREMENT_GROUP",
                    message=f"Requirement group '{g.name}' has no assigned courses and no sub-groups.",
                    entity_type="RequirementGroup",
                    entity_id=str(g.id),
                )
            )

    # 3. Prerequisite Rules Validation, Circularity & Missing References (via curriculum.graph)
    from curriculum.graph import detect_cycles
    from curriculum.services.graph_service import build_curriculum_version_graph

    rules = list(version.prerequisite_rules.select_related("course").all())

    for rule in rules:
        course_code = rule.course.code.upper()
        # Schema validation
        try:
            validate_rule_strict(rule.rule_json)
        except (RuleValidationError, ValueError) as exc:
            errors.append(
                ValidationErrorDetail(
                    code="INVALID_RULE_AST",
                    message=f"Prerequisite rule for {course_code} is invalid: {exc}",
                    entity_type="PrerequisiteRule",
                    entity_id=str(rule.id),
                )
            )

    # Build CurriculumGraph and detect cycles
    graph = build_curriculum_version_graph(version)
    cycle_check = detect_cycles(graph)
    if cycle_check.has_cycle:
        for cycle in cycle_check.cycles:
            cycle_str = " -> ".join(cycle)
            errors.append(
                ValidationErrorDetail(
                    code="CIRCULAR_PREREQUISITE",
                    message=f"Circular prerequisite detected: {cycle_str}",
                    entity_type="PrerequisiteRule",
                    details={"cycle": cycle},
                )
            )

    # Audit missing course references in prerequisite rules
    missing_courses = graph.get_missing_course_references()
    for missing_code in missing_courses:
        warnings.append(
            ValidationWarningDetail(
                code="MISSING_COURSE_REFERENCE",
                message=f"Prerequisite rule references course '{missing_code}' which is not in this curriculum version's courses.",
                entity_type="PrerequisiteRule",
                details={"course_code": missing_code},
            )
        )

    return ValidationReport(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
