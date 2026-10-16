"""
Career Course Recommendation Service (Prompt 08D).
Generates explainable, deterministically ranked course recommendations that
bridge a student's skill gap for target career objectives while strictly
respecting prerequisite eligibility and never displacing mandatory degree requirements.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from academic_records.models import StudentRecord
from academic_records.services.context_builder import build_rule_context
from career_mapping.models import (
    PROFICIENCY_SCORES,
    CareerObjective,
    CourseSkillMapping,
    ProficiencyLevel,
)
from career_mapping.services.gap_service import analyze_skill_gap
from curriculum.models import Course, PrerequisiteRule, RequirementGroupCourse
from degree_audit.services.audit_service import run_degree_audit
from rule_engine.core import evaluate_rule


@dataclass
class RecommendedSkillCovered:
    skill_id: str
    skill_code: str
    skill_name: str
    proficiency_level: str
    is_critical: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CourseRecommendation:
    course_id: str
    course_code: str
    course_title: str
    credits: float
    relevance_score: float
    recommendation_type: str  # "DEGREE_AND_CAREER" or "CAREER_ELECTIVE"
    satisfies_degree_requirement_group: str | None
    is_prerequisite_eligible: bool
    prerequisite_status_message: str
    skills_covered: list[RecommendedSkillCovered] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "course_id": self.course_id,
            "course_code": self.course_code,
            "course_title": self.course_title,
            "credits": self.credits,
            "relevance_score": self.relevance_score,
            "recommendation_type": self.recommendation_type,
            "satisfies_degree_requirement_group": self.satisfies_degree_requirement_group,
            "is_prerequisite_eligible": self.is_prerequisite_eligible,
            "prerequisite_status_message": self.prerequisite_status_message,
            "skills_covered": [s.to_dict() for s in self.skills_covered],
            "explanation": self.explanation,
        }


def get_career_course_recommendations(
    student_record: StudentRecord,
    career_objective: CareerObjective | None = None,
    limit: int = 10,
) -> list[CourseRecommendation]:
    """
    Produces deterministically ranked course recommendations that address a student's
    skill gap toward their target career objective.

    INVARIANTS:
    1. Never displaces degree requirements: clearly distinguishes between
       "DEGREE_AND_CAREER" (fulfills an unmet degree group) and "CAREER_ELECTIVE".
    2. Prerequisite Safety: evaluates prerequisite rules via the rule engine
       and clearly notes eligibility status and blockers.
    3. Deterministic Ranking: sorted by (-relevance_score, -credits, course_code).
    """
    institution = student_record.institution
    pinned_curriculum = student_record.pinned_curriculum

    # 1. Run skill gap analysis to identify missing competencies
    gap_report = analyze_skill_gap(student_record, career_objective)

    unmet_target_skills: dict[str, dict[str, Any]] = {}
    for item in gap_report.missing_skills:
        unmet_target_skills[item.skill_code] = {
            "is_critical": item.is_critical,
            "min_score": item.min_proficiency_score,
            "skill": item,
        }
    for item in gap_report.proficiency_gaps:
        unmet_target_skills[item.skill_code] = {
            "is_critical": item.is_critical,
            "min_score": item.min_proficiency_score,
            "skill": item,
        }

    if not unmet_target_skills:
        return []

    # 2. Identify completed or in-progress courses to avoid recommending already taken courses
    rule_context = build_rule_context(student_record)
    excluded_courses = set(rule_context.completed_courses) | set(rule_context.in_progress_courses)

    # 3. Identify unmet degree requirement groups in student's pinned curriculum
    audit = run_degree_audit(student_record, is_simulation=True)
    unmet_group_names = {g.name for g in audit.groups if not g.is_satisfied}

    unmet_group_course_map: dict[str, str] = {}
    if unmet_group_names and pinned_curriculum:
        rg_courses = RequirementGroupCourse.objects.filter(
            requirement_group__curriculum_version=pinned_curriculum,
            requirement_group__name__in=unmet_group_names,
        ).select_related("requirement_group", "course")
        for rgc in rg_courses:
            unmet_group_course_map[rgc.course.code] = rgc.requirement_group.name

    # 4. Find all candidate courses delivering unmet target skills
    unmet_skill_codes = list(unmet_target_skills.keys())
    candidate_mappings = (
        CourseSkillMapping.objects.filter(
            institution=institution,
            skill__code__in=unmet_skill_codes,
            course__is_active=True,
        )
        .exclude(course__code__in=excluded_courses)
        .select_related("course", "skill")
    )

    # Group mappings by candidate course
    course_to_mappings: dict[str, list[CourseSkillMapping]] = {}
    course_lookup: dict[str, Course] = {}

    for cm in candidate_mappings:
        code = cm.course.code
        course_to_mappings.setdefault(code, []).append(cm)
        course_lookup[code] = cm.course

    recommendations: list[CourseRecommendation] = []

    # 5. Score and evaluate each candidate course
    for code, mappings in course_to_mappings.items():
        course = course_lookup[code]

        # Degree requirement alignment
        satisfies_group = unmet_group_course_map.get(code)
        if satisfies_group:
            rec_type = "DEGREE_AND_CAREER"
            degree_bonus = 5.0
        else:
            rec_type = "CAREER_ELECTIVE"
            degree_bonus = 0.0

        # Prerequisite eligibility check using rule engine
        is_eligible = True
        prereq_msg = "No prerequisites required"

        if pinned_curriculum:
            prereq_rule = PrerequisiteRule.objects.filter(
                curriculum_version=pinned_curriculum,
                course=course,
            ).first()
            if prereq_rule and prereq_rule.rule_json:
                eval_res = evaluate_rule(prereq_rule.rule_json, rule_context)
                is_eligible = eval_res.eligible
                if is_eligible:
                    prereq_msg = "Prerequisites satisfied"
                else:
                    blockers_str = "; ".join(eval_res.blocking_reasons)
                    prereq_msg = f"Prerequisite requirement not met: {blockers_str}"

        eligibility_bonus = 2.0 if is_eligible else 0.0

        # Skill relevance scoring
        skill_score = 0.0
        covered_skills_list: list[RecommendedSkillCovered] = []
        critical_covered_names: list[str] = []
        recommended_covered_names: list[str] = []

        for cm in mappings:
            target_meta = unmet_target_skills.get(cm.skill.code)
            if not target_meta:
                continue

            is_crit = target_meta["is_critical"]
            min_score = target_meta["min_score"]
            weight = float(cm.coverage_weight)
            level_score = PROFICIENCY_SCORES.get(ProficiencyLevel(cm.proficiency_level), 2)

            base_val = 3.0 if is_crit else 1.5
            skill_score += base_val * weight

            if level_score >= min_score:
                skill_score += 1.0  # Full target proficiency bonus

            covered_skills_list.append(
                RecommendedSkillCovered(
                    skill_id=str(cm.skill.id),
                    skill_code=cm.skill.code,
                    skill_name=cm.skill.name,
                    proficiency_level=cm.proficiency_level,
                    is_critical=is_crit,
                )
            )

            if is_crit:
                critical_covered_names.append(f"{cm.skill.name} ({cm.proficiency_level})")
            else:
                recommended_covered_names.append(f"{cm.skill.name} ({cm.proficiency_level})")

        total_relevance = skill_score + degree_bonus + eligibility_bonus

        # Build clear human-readable explanation
        explanation_parts: list[str] = []
        if satisfies_group:
            explanation_parts.append(
                f"Fulfills unmet degree requirement '{satisfies_group}'."
            )
        else:
            explanation_parts.append(
                "Counts toward degree elective credits."
            )

        if critical_covered_names:
            explanation_parts.append(
                f"Addresses missing critical skills: {', '.join(critical_covered_names)}."
            )
        if recommended_covered_names:
            explanation_parts.append(
                f"Addresses recommended skills: {', '.join(recommended_covered_names)}."
            )

        if is_eligible:
            explanation_parts.append("Student is eligible to enroll.")
        else:
            explanation_parts.append(prereq_msg)

        full_explanation = " ".join(explanation_parts)

        # Sort covered skills deterministically by criticality then name
        covered_skills_list.sort(key=lambda s: (not s.is_critical, s.skill_name))

        recommendations.append(
            CourseRecommendation(
                course_id=str(course.id),
                course_code=course.code,
                course_title=course.title,
                credits=float(course.credits),
                relevance_score=round(total_relevance, 2),
                recommendation_type=rec_type,
                satisfies_degree_requirement_group=satisfies_group,
                is_prerequisite_eligible=is_eligible,
                prerequisite_status_message=prereq_msg,
                skills_covered=covered_skills_list,
                explanation=full_explanation,
            )
        )

    # 6. Deterministic Sort: (-relevance_score, -credits, course_code)
    recommendations.sort(
        key=lambda r: (-r.relevance_score, -r.credits, r.course_code)
    )

    return recommendations[:limit]
