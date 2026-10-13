import json
from decimal import Decimal
from pathlib import Path

import pytest

from rule_engine.core import (
    CompletedCourse,
    EvaluationResult,
    Exemption,
    RuleContext,
    TransferCredit,
    evaluate_rule,
)


def load_fixtures():
    fixtures_path = (
        Path(__file__).resolve().parent.parent / "rule_engine" / "fixtures" / "scenarios.json"
    )
    with open(fixtures_path, "r", encoding="utf-8") as f:
        return json.load(f)


FIXTURES = load_fixtures()


def test_fixture_count_threshold():
    """
    Enforces that the scenario library contains at least 60 distinct scenarios.
    """
    assert len(FIXTURES) >= 60, f"Expected at least 60 test scenarios, found {len(FIXTURES)}."


def parse_context(raw: dict) -> RuleContext:
    completed = [
        CompletedCourse(
            course_code=c["course_code"],
            grade=c["grade"],
            credits=Decimal(str(c["credits"])),
            status=c.get("status", "completed"),
            attempt_number=c.get("attempt_number", 1),
            term=c.get("term"),
        )
        for c in raw.get("completed_courses", [])
    ]

    transfers = [
        TransferCredit(
            course_code=tc["course_code"],
            credits=Decimal(str(tc["credits"])),
            verified=tc.get("verified", True),
            grade=tc.get("grade", "CR"),
        )
        for tc in raw.get("transfer_credits", [])
    ]

    exemptions = [
        Exemption(
            course_code=ex["course_code"],
            verified=ex.get("verified", True),
        )
        for ex in raw.get("exemptions", [])
    ]

    credits_by_category = {
        cat: Decimal(str(val)) for cat, val in raw.get("credits_by_category", {}).items()
    }

    total_credits = (
        Decimal(str(raw["total_credits"])) if raw.get("total_credits") is not None else None
    )

    cgpa = Decimal(str(raw["cgpa"])) if raw.get("cgpa") is not None else None

    grade_scale = raw.get("grade_scale")
    repeated_policy = raw.get("repeated_course_policy", "best_grade")

    kwargs = {
        "completed_courses": completed,
        "in_progress_courses": set(raw.get("in_progress_courses", [])),
        "planned_same_term_courses": set(raw.get("planned_same_term_courses", [])),
        "transfer_credits": transfers,
        "exemptions": exemptions,
        "credits_by_category": credits_by_category,
        "total_credits": total_credits,
        "cgpa": cgpa,
        "curriculum_version_id": raw.get("curriculum_version_id"),
        "repeated_course_policy": repeated_policy,
    }
    if grade_scale:
        kwargs["grade_scale"] = grade_scale

    return RuleContext(**kwargs)


@pytest.mark.parametrize("scenario", FIXTURES, ids=[s["id"] for s in FIXTURES])
def test_evaluate_scenario_fixture(scenario):
    """
    Evaluates individual rule engine fixture against expected result.
    Also validates determinism (evaluating same input twice yields identical results).
    """
    rule = scenario["rule"]
    ctx = parse_context(scenario["context"])
    expected = scenario["expected"]

    # First evaluation
    result1: EvaluationResult = evaluate_rule(rule, ctx)

    assert result1.eligible == expected["eligible"], (
        f"Scenario {scenario['id']} ({scenario['description']}) eligibility mismatch: "
        f"got {result1.eligible}, expected {expected['eligible']}."
    )
    assert result1.status.value == expected["status"], (
        f"Scenario {scenario['id']} status mismatch: "
        f"got {result1.status.value}, expected {expected['status']}."
    )
    assert list(result1.blocking_reasons) == expected["blocking_reasons"], (
        f"Scenario {scenario['id']} blocking reasons mismatch:\n"
        f"Got:      {list(result1.blocking_reasons)}\n"
        f"Expected: {expected['blocking_reasons']}"
    )

    # Second evaluation (determinism assertion)
    result2: EvaluationResult = evaluate_rule(rule, ctx)
    assert result1.eligible == result2.eligible
    assert result1.status == result2.status
    assert result1.blocking_reasons == result2.blocking_reasons
    assert result1.node_results.to_dict() == result2.node_results.to_dict()
