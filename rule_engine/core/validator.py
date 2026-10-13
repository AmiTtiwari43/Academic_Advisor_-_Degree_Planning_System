"""
Prerequisite Rule Validator (v1).
Pure Python. Deterministic AST traversal and schema validation.
"""

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Union

from rule_engine.core.schema import (
    COMBINATOR_OPERATORS,
    MAX_CONDITIONS,
    MAX_DEPTH,
    MAX_SIZE_BYTES,
    MAX_STRING_LENGTH,
    OPERATOR_ALLOWED_FIELDS,
    OPERATOR_REQUIRED_FIELDS,
    SCHEMA_VERSION,
    VALID_OPERATORS,
)


class RuleValidationError(ValueError):
    """
    Raised when a rule document violates grammar v1 constraints.
    Attributes include path-addressed location (e.g. '$.conditions[2].min_credits').
    """

    def __init__(self, message: str, path: str = "$"):
        full_msg = f"{path}: {message}"
        super().__init__(full_msg)
        self.path = path
        self.raw_message = message


def _is_numeric(val: Any) -> bool:
    """Checks if value is a valid numeric quantity without accepting booleans."""
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float, Decimal)):
        return True
    if isinstance(val, str):
        try:
            Decimal(val)
            return True
        except (InvalidOperation, ValueError):
            return False
    return False


def _to_decimal(val: Any) -> Decimal:
    return Decimal(str(val))


class RuleValidator:
    """
    Validates a rule document against Grammar v1 specification.
    """

    def __init__(
        self,
        max_depth: int = MAX_DEPTH,
        max_conditions: int = MAX_CONDITIONS,
        max_size_bytes: int = MAX_SIZE_BYTES,
        max_string_length: int = MAX_STRING_LENGTH,
    ):
        self.max_depth = max_depth
        self.max_conditions = max_conditions
        self.max_size_bytes = max_size_bytes
        self.max_string_length = max_string_length

    def validate(self, rule: Union[dict, str]) -> list[str]:
        """
        Validates the rule document and returns a list of path-addressed errors.
        Returns an empty list if valid.
        """
        errors: list[str] = []

        # 1. Payload size check
        if isinstance(rule, str):
            encoded = rule.encode("utf-8")
            if len(encoded) > self.max_size_bytes:
                return [
                    f"$: Serialized rule size ({len(encoded)} bytes) exceeds maximum limit ({self.max_size_bytes} bytes)."
                ]
            try:
                data = json.loads(rule)
            except json.JSONDecodeError as exc:
                return [f"$: Invalid JSON payload: {exc}"]
        elif isinstance(rule, dict):
            # Check serialized size
            try:
                serialized = json.dumps(rule)
                if len(serialized.encode("utf-8")) > self.max_size_bytes:
                    return [
                        f"$: Serialized rule size ({len(serialized)} bytes) exceeds maximum limit ({self.max_size_bytes} bytes)."
                    ]
            except (TypeError, ValueError) as exc:
                return [f"$: Rule document cannot be serialized to JSON: {exc}"]
            data = rule
        else:
            return ["$: Rule document must be a JSON object or string."]

        if not isinstance(data, dict):
            return ["$: Rule document must be a JSON object."]

        # 2. Schema version check
        schema_version = data.get("schema_version")
        if schema_version is None:
            errors.append("$.schema_version: Missing required field 'schema_version'.")
        elif (
            isinstance(schema_version, bool)
            or not isinstance(schema_version, int)
            or schema_version != SCHEMA_VERSION
        ):
            errors.append(
                f"$.schema_version: Unsupported or invalid schema_version {schema_version!r}; expected {SCHEMA_VERSION}."
            )

        # 3. Recursive AST node validation
        condition_count = [0]
        self._validate_node(data, path="$", depth=1, errors=errors, condition_count=condition_count)

        if condition_count[0] > self.max_conditions:
            errors.append(
                f"$: Rule condition count ({condition_count[0]}) exceeds maximum limit of {self.max_conditions}."
            )

        return errors

    def _validate_node(
        self,
        node: Any,
        path: str,
        depth: int,
        errors: list[str],
        condition_count: list[int],
    ) -> None:
        if not isinstance(node, dict):
            errors.append(f"{path}: Expected JSON object, got {type(node).__name__}.")
            return

        condition_count[0] += 1

        if depth > self.max_depth:
            errors.append(
                f"{path}: Nesting depth ({depth}) exceeds maximum limit ({self.max_depth})."
            )
            return

        op_type = node.get("type")
        if not op_type:
            errors.append(f"{path}.type: Missing required field 'type'.")
            return

        if not isinstance(op_type, str):
            errors.append(
                f"{path}.type: Field 'type' must be a string, got {type(op_type).__name__}."
            )
            return

        if op_type not in VALID_OPERATORS:
            errors.append(f"{path}.type: Unknown operator '{op_type}'.")
            return

        # Check allowed and required keys
        allowed_keys = OPERATOR_ALLOWED_FIELDS[op_type]
        if path == "$":
            allowed_keys = allowed_keys | {"schema_version", "rule_id", "description"}

        for key in node:
            if key not in allowed_keys:
                errors.append(
                    f"{path}.{key}: Unknown or disallowed key '{key}' for operator '{op_type}'."
                )

        required_keys = OPERATOR_REQUIRED_FIELDS[op_type]
        for req in required_keys:
            if req not in node:
                errors.append(
                    f"{path}.{req}: Missing required field '{req}' for operator '{op_type}'."
                )

        # Specific operator validations
        if op_type == "course_completed":
            self._validate_string_field(
                node, "course_code", f"{path}.course_code", errors, required=True
            )
            self._validate_string_field(
                node, "min_grade", f"{path}.min_grade", errors, required=False
            )

        elif op_type == "credits_completed":
            val = node.get("min_credits")
            if val is not None:
                if not _is_numeric(val):
                    errors.append(
                        f"{path}.min_credits: 'min_credits' must be a positive number, got {val!r}."
                    )
                else:
                    dec = _to_decimal(val)
                    if dec < Decimal("0"):
                        errors.append(
                            f"{path}.min_credits: 'min_credits' must be greater than or equal to 0, got {val!r}."
                        )
            self._validate_string_field(
                node, "category", f"{path}.category", errors, required=False
            )

        elif op_type == "cgpa_min":
            val = node.get("value")
            if val is not None:
                if not _is_numeric(val):
                    errors.append(f"{path}.value: 'value' must be a numeric CGPA, got {val!r}.")
                else:
                    dec = _to_decimal(val)
                    if dec < Decimal("0"):
                        errors.append(
                            f"{path}.value: 'value' must be greater than or equal to 0, got {val!r}."
                        )

        elif op_type in ("corequisite", "anti_requisite"):
            self._validate_string_field(
                node, "course_code", f"{path}.course_code", errors, required=True
            )

        elif op_type in COMBINATOR_OPERATORS:
            conditions = node.get("conditions")
            if conditions is None:
                errors.append(f"{path}.conditions: Missing required field 'conditions'.")
            elif not isinstance(conditions, list):
                errors.append(
                    f"{path}.conditions: 'conditions' must be a list of condition objects, got {type(conditions).__name__}."
                )
            elif len(conditions) == 0:
                errors.append(
                    f"{path}.conditions: Combinator '{op_type}' must contain at least one condition."
                )
            else:
                for idx, child in enumerate(conditions):
                    child_path = f"{path}.conditions[{idx}]"
                    self._validate_node(
                        child,
                        path=child_path,
                        depth=depth + 1,
                        errors=errors,
                        condition_count=condition_count,
                    )

    def _validate_string_field(
        self,
        node: dict,
        field_name: str,
        path: str,
        errors: list[str],
        required: bool = False,
    ) -> None:
        val = node.get(field_name)
        if val is None:
            if required:
                errors.append(f"{path}: Field '{field_name}' is required.")
            return
        if not isinstance(val, str):
            errors.append(
                f"{path}: Field '{field_name}' must be a string, got {type(val).__name__}."
            )
            return
        if len(val.strip()) == 0:
            errors.append(f"{path}: Field '{field_name}' cannot be empty.")
            return
        if len(val) > self.max_string_length:
            errors.append(
                f"{path}: String length ({len(val)}) exceeds maximum limit of {self.max_string_length} characters."
            )


def validate_rule(rule: Union[dict, str]) -> list[str]:
    """Helper returning list of validation errors."""
    return RuleValidator().validate(rule)


def validate_rule_strict(rule: Union[dict, str]) -> None:
    """Helper raising RuleValidationError if invalid."""
    errors = validate_rule(rule)
    if errors:
        raise RuleValidationError(errors[0])
