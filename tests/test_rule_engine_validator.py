import json

import pytest

from rule_engine.core import (
    RuleValidationError,
    validate_rule,
    validate_rule_strict,
)


def test_validator_accepts_valid_minimal_rule():
    rule = {"schema_version": 1, "type": "course_completed", "course_code": "CS 101"}
    errors = validate_rule(rule)
    assert errors == []


def test_validator_rejects_missing_schema_version():
    rule = {"type": "course_completed", "course_code": "CS 101"}
    errors = validate_rule(rule)
    assert any("$.schema_version: Missing required field" in e for e in errors)


def test_validator_rejects_unsupported_schema_version():
    rule = {"schema_version": 2, "type": "course_completed", "course_code": "CS 101"}
    errors = validate_rule(rule)
    assert any("$.schema_version: Unsupported or invalid schema_version" in e for e in errors)


def test_validator_rejects_unknown_operator():
    rule = {"schema_version": 1, "type": "magic_check", "course_code": "CS 101"}
    errors = validate_rule(rule)
    assert any("$.type: Unknown operator 'magic_check'" in e for e in errors)


def test_validator_rejects_disallowed_extra_keys():
    rule = {
        "schema_version": 1,
        "type": "course_completed",
        "course_code": "CS 101",
        "unexpected_key": "some_value",
    }
    errors = validate_rule(rule)
    assert any("$.unexpected_key: Unknown or disallowed key" in e for e in errors)


def test_validator_rejects_missing_required_field():
    rule = {"schema_version": 1, "type": "course_completed"}
    errors = validate_rule(rule)
    assert any("$.course_code: Missing required field 'course_code'" in e for e in errors)


def test_validator_rejects_empty_string_field():
    rule = {"schema_version": 1, "type": "course_completed", "course_code": "   "}
    errors = validate_rule(rule)
    assert any("$.course_code: Field 'course_code' cannot be empty" in e for e in errors)


def test_validator_rejects_wrong_type_in_field():
    rule = {"schema_version": 1, "type": "course_completed", "course_code": 101}
    errors = validate_rule(rule)
    assert any("$.course_code: Field 'course_code' must be a string" in e for e in errors)


def test_validator_rejects_boolean_as_numeric_credits():
    rule = {"schema_version": 1, "type": "credits_completed", "min_credits": True}
    errors = validate_rule(rule)
    assert any("$.min_credits: 'min_credits' must be a positive number" in e for e in errors)


def test_validator_rejects_boolean_as_numeric_cgpa():
    rule = {"schema_version": 1, "type": "cgpa_min", "value": False}
    errors = validate_rule(rule)
    assert any("$.value: 'value' must be a numeric CGPA" in e for e in errors)


def test_validator_rejects_negative_credits():
    rule = {"schema_version": 1, "type": "credits_completed", "min_credits": -5.0}
    errors = validate_rule(rule)
    assert any(
        "$.min_credits: 'min_credits' must be greater than or equal to 0" in e for e in errors
    )


def test_validator_rejects_empty_combinator():
    rule = {"schema_version": 1, "type": "all_of", "conditions": []}
    errors = validate_rule(rule)
    assert any(
        "$.conditions: Combinator 'all_of' must contain at least one condition" in e for e in errors
    )


def test_validator_rejects_non_list_conditions():
    rule = {"schema_version": 1, "type": "all_of", "conditions": "not_a_list"}
    errors = validate_rule(rule)
    assert any(
        "$.conditions: 'conditions' must be a list of condition objects" in e for e in errors
    )


def test_validator_depth_limit_depth_8_accepted():
    # Build depth 8 tree
    curr = {"type": "course_completed", "course_code": "CS 101"}
    for _ in range(7):
        curr = {"type": "all_of", "conditions": [curr]}
    curr["schema_version"] = 1

    errors = validate_rule(curr)
    assert errors == []


def test_validator_depth_limit_depth_9_rejected():
    # Build depth 9 tree
    curr = {"type": "course_completed", "course_code": "CS 101"}
    for _ in range(8):
        curr = {"type": "all_of", "conditions": [curr]}
    curr["schema_version"] = 1

    errors = validate_rule(curr)
    assert any("Nesting depth (9) exceeds maximum limit (8)" in e for e in errors)


def test_validator_condition_count_limit_100_accepted():
    # 1 root + 99 children = 100 conditions
    children = [{"type": "course_completed", "course_code": f"CS {i}"} for i in range(99)]
    rule = {"schema_version": 1, "type": "all_of", "conditions": children}

    errors = validate_rule(rule)
    assert errors == []


def test_validator_condition_count_limit_101_rejected():
    # 1 root + 100 children = 101 conditions
    children = [{"type": "course_completed", "course_code": f"CS {i}"} for i in range(100)]
    rule = {"schema_version": 1, "type": "all_of", "conditions": children}

    errors = validate_rule(rule)
    assert any("Rule condition count (101) exceeds maximum limit of 100" in e for e in errors)


def test_validator_oversized_payload_rejected():
    # Payload > 32 KB (32,768 bytes)
    giant_string = "A" * 33000
    rule = {"schema_version": 1, "type": "course_completed", "course_code": giant_string}

    errors = validate_rule(rule)
    assert any("exceeds maximum limit (32768 bytes)" in e or "String length" in e for e in errors)


def test_validator_string_length_limit_rejected():
    long_code = "CS " + ("X" * 2005)
    rule = {"schema_version": 1, "type": "course_completed", "course_code": long_code}

    errors = validate_rule(rule)
    assert any("String length (2008) exceeds maximum limit of 2000 characters" in e for e in errors)


def test_validate_rule_strict_raises_exception():
    rule = {"schema_version": 1, "type": "unknown_op"}
    with pytest.raises(RuleValidationError) as exc_info:
        validate_rule_strict(rule)
    assert "$.type: Unknown operator 'unknown_op'" in str(exc_info.value)


def test_validator_rejects_invalid_json_string():
    errors = validate_rule("{invalid_json: true")
    assert any("Invalid JSON payload" in e for e in errors)


def test_validator_rejects_non_dict_non_string():
    errors = validate_rule(12345)  # type: ignore[arg-type]
    assert any("Rule document must be a JSON object or string" in e for e in errors)


def test_validator_rejects_json_array_root():
    errors = validate_rule("[]")
    assert any("Rule document must be a JSON object" in e for e in errors)


def test_validator_accepts_valid_json_string():
    raw = json.dumps({"schema_version": 1, "type": "course_completed", "course_code": "CS 101"})
    errors = validate_rule(raw)
    assert errors == []


def test_evaluate_rule_with_json_string_and_result_to_dict():
    from decimal import Decimal

    from rule_engine.core import CompletedCourse, RuleContext, evaluate_rule

    raw = json.dumps({"schema_version": 1, "type": "course_completed", "course_code": "CS 101"})
    ctx = RuleContext(
        completed_courses=[CompletedCourse(course_code="CS 101", grade="A", credits=Decimal("3.0"))]
    )
    res = evaluate_rule(raw, ctx)
    assert res.eligible is True
    d = res.to_dict()
    assert d["eligible"] is True
    assert d["status"] == "SATISFIED"
    assert "node_results" in d
