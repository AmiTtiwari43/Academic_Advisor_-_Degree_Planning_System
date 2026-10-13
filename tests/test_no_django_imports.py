import os
import subprocess
import sys


def test_no_django_or_rest_framework_imports():
    """
    Verify that rule_engine.core imports strictly zero Django, DRF, or app settings modules.
    Must be fully independent and functional in an isolated Python interpreter.
    """
    code = """
import sys
# Ensure no django settings env var is set
import os
os.environ.pop("DJANGO_SETTINGS_MODULE", None)

from rule_engine.core import (
    evaluate_rule,
    validate_rule,
    RuleContext,
    CompletedCourse,
    EvaluationStatus,
)
from decimal import Decimal

# Check sys.modules
forbidden = [m for m in sys.modules if m.startswith("django") or m.startswith("rest_framework") or m.startswith("config")]
if forbidden:
    print(f"FORBIDDEN_MODULES_FOUND: {forbidden}")
    sys.exit(1)

# Execute evaluation
rule = {"schema_version": 1, "type": "course_completed", "course_code": "CS 101"}
ctx = RuleContext(completed_courses=[CompletedCourse(course_code="CS 101", grade="A", credits=Decimal("3.0"))])
res = evaluate_rule(rule, ctx)
assert res.eligible is True
assert res.status == EvaluationStatus.SATISFIED
print("STANDALONE_SUCCESS")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"},
    )

    assert result.returncode == 0, f"Standalone evaluation failed: {result.stderr or result.stdout}"
    assert "STANDALONE_SUCCESS" in result.stdout
    assert "FORBIDDEN_MODULES_FOUND" not in result.stdout
