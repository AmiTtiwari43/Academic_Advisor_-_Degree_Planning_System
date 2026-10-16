"""
Skill-Gap Analysis Service (Prompt 08D).
Evaluates student transcript against career objective skill requirements
to identify acquired skills, missing competencies, and readiness percentage.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from academic_records.models import (
    StudentRecord,
    TranscriptEntry,
    TranscriptEntryStatus,
    VerificationStatus,
)
from career_mapping.models import (
    PROFICIENCY_SCORES,
    CareerObjective,
    CourseSkillMapping,
    ProficiencyLevel,
    StudentCareerPreference,
)


@dataclass
class AcquiredSkillInfo:
    skill_id: str
    skill_code: str
    skill_name: str
    skill_category: str
    proficiency_level: str
    proficiency_score: int
    source_courses: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TargetSkillRequirement:
    skill_id: str
    skill_code: str
    skill_name: str
    skill_category: str
    min_proficiency: str
    min_proficiency_score: int
    is_critical: bool
    is_met: bool
    current_proficiency: str | None = None
    current_proficiency_score: int = 0
    status: str = "MISSING"  # "SATISFIED", "PROFICIENCY_GAP", "MISSING"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SkillGapReport:
    student_id: str
    student_username: str
    career_objective_id: str
    career_objective_code: str
    career_objective_title: str
    total_target_skills: int
    total_critical_skills: int
    critical_skills_met: int
    recommended_skills_met: int
    readiness_percentage: float
    satisfied_skills: list[TargetSkillRequirement] = field(default_factory=list)
    proficiency_gaps: list[TargetSkillRequirement] = field(default_factory=list)
    missing_skills: list[TargetSkillRequirement] = field(default_factory=list)
    acquired_skills: list[AcquiredSkillInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "student_id": self.student_id,
            "student_username": self.student_username,
            "career_objective_id": self.career_objective_id,
            "career_objective_code": self.career_objective_code,
            "career_objective_title": self.career_objective_title,
            "total_target_skills": self.total_target_skills,
            "total_critical_skills": self.total_critical_skills,
            "critical_skills_met": self.critical_skills_met,
            "recommended_skills_met": self.recommended_skills_met,
            "readiness_percentage": self.readiness_percentage,
            "satisfied_skills": [s.to_dict() for s in self.satisfied_skills],
            "proficiency_gaps": [g.to_dict() for g in self.proficiency_gaps],
            "missing_skills": [m.to_dict() for m in self.missing_skills],
            "acquired_skills": [a.to_dict() for a in self.acquired_skills],
        }


def compute_student_acquired_skills(student_record: StudentRecord) -> dict[str, AcquiredSkillInfo]:
    """
    Computes all skills acquired by a student through verified, completed coursework.
    For skills covered by multiple courses, resolves to the highest proficiency achieved.
    """
    completed_entries = list(
        TranscriptEntry.objects.filter(
            student_record=student_record,
            status=TranscriptEntryStatus.COMPLETED,
            verification_status__in=[
                VerificationStatus.VERIFIED,
                VerificationStatus.OFFICIAL_SEALED,
            ],
        ).select_related("course")
    )

    passing_courses = [
        e.course
        for e in completed_entries
        if e.grade.upper() not in ("F", "W", "I", "")
    ]

    if not passing_courses:
        return {}

    mappings = list(
        CourseSkillMapping.objects.filter(
            course__in=passing_courses
        ).select_related("skill", "course")
    )

    acquired: dict[str, AcquiredSkillInfo] = {}

    for m in mappings:
        skill = m.skill
        level = m.proficiency_level
        score = PROFICIENCY_SCORES.get(ProficiencyLevel(level), 1)

        if skill.code in acquired:
            existing = acquired[skill.code]
            if score > existing.proficiency_score:
                existing.proficiency_level = level
                existing.proficiency_score = score
            if m.course.code not in existing.source_courses:
                existing.source_courses.append(m.course.code)
                existing.source_courses.sort()
        else:
            acquired[skill.code] = AcquiredSkillInfo(
                skill_id=str(skill.id),
                skill_code=skill.code,
                skill_name=skill.name,
                skill_category=skill.category,
                proficiency_level=level,
                proficiency_score=score,
                source_courses=[m.course.code],
            )

    return acquired


def analyze_skill_gap(
    student_record: StudentRecord,
    career_objective: CareerObjective | None = None,
) -> SkillGapReport:
    """
    Performs gap analysis comparing a student's acquired skills against
    the skill requirements of a specified career objective (or primary preference).
    """
    if career_objective is None:
        primary_pref = (
            StudentCareerPreference.objects.filter(student_record=student_record)
            .order_by("priority")
            .select_related("career_objective")
            .first()
        )
        if primary_pref:
            career_objective = primary_pref.career_objective
        else:
            raise ValueError("No career objective specified and no career preference recorded for student.")

    acquired_map = compute_student_acquired_skills(student_record)

    requirements = list(
        career_objective.skill_requirements.select_related("skill").order_by(
            "-is_critical", "display_order", "skill__name"
        )
    )

    satisfied_skills: list[TargetSkillRequirement] = []
    proficiency_gaps: list[TargetSkillRequirement] = []
    missing_skills: list[TargetSkillRequirement] = []

    total_critical = 0
    critical_met = 0
    recommended_met = 0

    total_possible_score = 0.0
    earned_score = 0.0

    for req in requirements:
        skill = req.skill
        min_level = req.min_proficiency
        min_score = PROFICIENCY_SCORES.get(ProficiencyLevel(min_level), 2)
        weight = 2.0 if req.is_critical else 1.0

        if req.is_critical:
            total_critical += 1
        total_possible_score += weight

        acquired_info = acquired_map.get(skill.code)

        if acquired_info:
            curr_score = acquired_info.proficiency_score
            curr_level = acquired_info.proficiency_level

            if curr_score >= min_score:
                status = "SATISFIED"
                earned_score += weight
                if req.is_critical:
                    critical_met += 1
                else:
                    recommended_met += 1
                satisfied_skills.append(
                    TargetSkillRequirement(
                        skill_id=str(skill.id),
                        skill_code=skill.code,
                        skill_name=skill.name,
                        skill_category=skill.category,
                        min_proficiency=min_level,
                        min_proficiency_score=min_score,
                        is_critical=req.is_critical,
                        is_met=True,
                        current_proficiency=curr_level,
                        current_proficiency_score=curr_score,
                        status=status,
                    )
                )
            else:
                status = "PROFICIENCY_GAP"
                # Partial credit proportional to achieved score
                earned_score += weight * (curr_score / min_score) * 0.7
                proficiency_gaps.append(
                    TargetSkillRequirement(
                        skill_id=str(skill.id),
                        skill_code=skill.code,
                        skill_name=skill.name,
                        skill_category=skill.category,
                        min_proficiency=min_level,
                        min_proficiency_score=min_score,
                        is_critical=req.is_critical,
                        is_met=False,
                        current_proficiency=curr_level,
                        current_proficiency_score=curr_score,
                        status=status,
                    )
                )
        else:
            status = "MISSING"
            missing_skills.append(
                TargetSkillRequirement(
                    skill_id=str(skill.id),
                    skill_code=skill.code,
                    skill_name=skill.name,
                    skill_category=skill.category,
                    min_proficiency=min_level,
                    min_proficiency_score=min_score,
                    is_critical=req.is_critical,
                    is_met=False,
                    current_proficiency=None,
                    current_proficiency_score=0,
                    status=status,
                )
            )

    readiness_percentage = (
        round((earned_score / total_possible_score) * 100.0, 1)
        if total_possible_score > 0
        else 100.0
    )

    return SkillGapReport(
        student_id=str(student_record.id),
        student_username=student_record.student.username,
        career_objective_id=str(career_objective.id),
        career_objective_code=career_objective.code,
        career_objective_title=career_objective.title,
        total_target_skills=len(requirements),
        total_critical_skills=total_critical,
        critical_skills_met=critical_met,
        recommended_skills_met=recommended_met,
        readiness_percentage=min(100.0, readiness_percentage),
        satisfied_skills=satisfied_skills,
        proficiency_gaps=proficiency_gaps,
        missing_skills=missing_skills,
        acquired_skills=list(acquired_map.values()),
    )
