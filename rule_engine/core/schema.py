"""
Prerequisite Rule Grammar Schema & Constants (v1).
Independent of Django. Pure Python.
"""

from typing import Final

SCHEMA_VERSION: Final[int] = 1

# Guard limits
MAX_DEPTH: Final[int] = 8
MAX_CONDITIONS: Final[int] = 100
MAX_SIZE_BYTES: Final[int] = 32768  # 32 KB
MAX_STRING_LENGTH: Final[int] = 2000

# Operator Types
OP_COURSE_COMPLETED: Final[str] = "course_completed"
OP_CREDITS_COMPLETED: Final[str] = "credits_completed"
OP_CGPA_MIN: Final[str] = "cgpa_min"
OP_COREQUISITE: Final[str] = "corequisite"
OP_ANTI_REQUISITE: Final[str] = "anti_requisite"

OP_ALL_OF: Final[str] = "all_of"
OP_ANY_OF: Final[str] = "any_of"

LEAF_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        OP_COURSE_COMPLETED,
        OP_CREDITS_COMPLETED,
        OP_CGPA_MIN,
        OP_COREQUISITE,
        OP_ANTI_REQUISITE,
    }
)

COMBINATOR_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        OP_ALL_OF,
        OP_ANY_OF,
    }
)

VALID_OPERATORS: Final[frozenset[str]] = LEAF_OPERATORS | COMBINATOR_OPERATORS

# Allowed fields per operator
OPERATOR_ALLOWED_FIELDS: Final[dict[str, frozenset[str]]] = {
    OP_COURSE_COMPLETED: frozenset({"type", "course_code", "min_grade"}),
    OP_CREDITS_COMPLETED: frozenset({"type", "min_credits", "category"}),
    OP_CGPA_MIN: frozenset({"type", "value"}),
    OP_COREQUISITE: frozenset({"type", "course_code"}),
    OP_ANTI_REQUISITE: frozenset({"type", "course_code"}),
    OP_ALL_OF: frozenset({"type", "conditions"}),
    OP_ANY_OF: frozenset({"type", "conditions"}),
}

# Required fields per operator
OPERATOR_REQUIRED_FIELDS: Final[dict[str, frozenset[str]]] = {
    OP_COURSE_COMPLETED: frozenset({"type", "course_code"}),
    OP_CREDITS_COMPLETED: frozenset({"type", "min_credits"}),
    OP_CGPA_MIN: frozenset({"type", "value"}),
    OP_COREQUISITE: frozenset({"type", "course_code"}),
    OP_ANTI_REQUISITE: frozenset({"type", "course_code"}),
    OP_ALL_OF: frozenset({"type", "conditions"}),
    OP_ANY_OF: frozenset({"type", "conditions"}),
}
