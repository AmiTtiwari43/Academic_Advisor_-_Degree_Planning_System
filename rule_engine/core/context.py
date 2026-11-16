"""
Evaluation Context Dataclasses (v1).
Pure Python. Zero external dependencies.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class RepeatedCoursePolicy(str, Enum):
    BEST_GRADE = "best_grade"
    LATEST = "latest"


DEFAULT_GRADE_SCALE: dict[str, float] = {
    "A+": 10.0,
    "A": 9.0,
    "A-": 8.5,
    "B+": 8.0,
    "B": 7.0,
    "B-": 6.5,
    "C+": 6.0,
    "C": 5.0,
    "C-": 4.5,
    "D+": 4.0,
    "D": 3.0,
    "F": 0.0,
}


@dataclass(frozen=True)
class CompletedCourse:
    course_code: str
    grade: str
    credits: Decimal
    status: str = "completed"
    attempt_number: int = 1
    term: Optional[str] = None


@dataclass(frozen=True)
class TransferCredit:
    course_code: str
    credits: Decimal
    verified: bool = True
    grade: Optional[str] = "CR"  # Credit granted


@dataclass(frozen=True)
class Exemption:
    course_code: str
    verified: bool = True


@dataclass
class RuleContext:
    completed_courses: list[CompletedCourse] = field(default_factory=list)
    in_progress_courses: set[str] = field(default_factory=set)
    planned_same_term_courses: set[str] = field(default_factory=set)
    transfer_credits: list[TransferCredit] = field(default_factory=list)
    exemptions: list[Exemption] = field(default_factory=list)
    credits_by_category: dict[str, Decimal] = field(default_factory=dict)
    total_credits: Optional[Decimal] = None
    cgpa: Optional[Decimal] = None
    curriculum_version_id: Optional[str] = None
    grade_scale: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_GRADE_SCALE))
    repeated_course_policy: str = RepeatedCoursePolicy.BEST_GRADE.value

    def get_effective_total_credits(self) -> Decimal:
        """
        Returns total credits. If not explicitly provided, sums unique earned courses + verified transfers.
        """
        if self.total_credits is not None:
            return self.total_credits

        seen_courses: set[str] = set()
        earned = Decimal("0")

        # Add transfer credits
        for tc in self.transfer_credits:
            if tc.verified and tc.course_code not in seen_courses:
                seen_courses.add(tc.course_code)
                earned += tc.credits

        # Add completed courses
        for cc in self.completed_courses:
            if cc.course_code not in seen_courses:
                seen_courses.add(cc.course_code)
                earned += cc.credits

        return earned
