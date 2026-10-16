"""
Curriculum Change Impact Analyzer Service.
Provides read-only assessment comparing draft vs published curriculum versions.
Computes newly unmet requirements, prerequisite eligibility changes, offering conflicts,
graduation delays, and affected student/plan drill-downs.

INVARIANT: Strictly read-only. Zero row mutations across all database tables.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.utils import timezone

from academic_records.models import StudentRecord
from academic_records.services.context_builder import build_rule_context
from curriculum.impact.models import (
    CurriculumImpactReport,
    ImpactSeverity,
    ImpactSummary,
    PlanImpactDetail,
    PrerequisiteChange,
    RequirementDiff,
    StudentImpactDetail,
)
from curriculum.models import (
    CurriculumStatus,
    CurriculumVersion,
    PrerequisiteRule,
    RequirementGroupCourse,
)
from degree_audit.services.audit_service import run_degree_audit
from planning.models import Plan, PlanStatus
from planning.services.simulation_service import simulate_plan
from rule_engine.core import evaluate_rule

logger = logging.getLogger(__name__)


def analyze_curriculum_change_impact(
    draft_version: CurriculumVersion,
    published_version: CurriculumVersion | None = None,
) -> CurriculumImpactReport:
    """
    Analyzes the potential impact of publishing a draft curriculum version by comparing
    it against the current published version for the same programme.

    Performs read-only simulations of all active students and plans.
    Guarantees zero database row mutations.
    """
    institution = draft_version.institution
    programme = draft_version.programme

    # 1. Resolve published baseline version
    if published_version is None:
        published_version = (
            CurriculumVersion.objects.filter(
                institution=institution,
                programme=programme,
                status=CurriculumStatus.PUBLISHED,
            )
            .order_by("-version_number")
            .first()
        )

    # If no prior published version exists, this is the inaugural curriculum
    if published_version is None:
        return CurriculumImpactReport(
            draft_version_id=str(draft_version.id),
            draft_version_number=draft_version.version_number,
            published_version_id="",
            published_version_number=0,
            programme_code=programme.code,
            programme_name=programme.name,
            summary=ImpactSummary(),
            requirement_changes=[],
            prerequisite_changes=[],
            affected_students=[],
            affected_plans=[],
            analyzed_at=timezone.now().isoformat(),
        )

    # 2. Structural Requirement Diffs
    requirement_diffs = _compute_requirement_diffs(published_version, draft_version)

    # 3. Prerequisite Rule Diffs
    prerequisite_diffs = _compute_prerequisite_diffs(published_version, draft_version)
    changed_rule_courses = {pc.course_code: pc for pc in prerequisite_diffs}

    # 4. Student Progress Impact (Degree Audit Re-evaluation)
    active_students = list(
        StudentRecord.objects.filter(
            institution=institution,
            programme=programme,
            status="ACTIVE",
        ).select_related("student", "pinned_curriculum")
    )

    affected_students: list[StudentImpactDetail] = []
    students_delayed_count = 0
    high_impact_count = 0
    moderate_impact_count = 0
    low_impact_count = 0

    for student in active_students:
        impact = _evaluate_student_impact(
            student=student,
            published_version=published_version,
            draft_version=draft_version,
            changed_rule_courses=changed_rule_courses,
        )
        if impact.severity != ImpactSeverity.NONE:
            affected_students.append(impact)
            if impact.severity == ImpactSeverity.HIGH:
                high_impact_count += 1
            elif impact.severity == ImpactSeverity.MODERATE:
                moderate_impact_count += 1
            elif impact.severity == ImpactSeverity.LOW:
                low_impact_count += 1

    # 5. Degree Plan Impact (Plan Simulation Re-evaluation)
    active_plans = list(
        Plan.objects.filter(
            institution=institution,
            student_record__programme=programme,
        )
        .exclude(status__in=[PlanStatus.ARCHIVED, PlanStatus.REJECTED])
        .select_related("student_record__student")
    )

    affected_plans: list[PlanImpactDetail] = []
    for plan in active_plans:
        plan_impact = _evaluate_plan_impact(
            plan=plan,
            published_version=published_version,
            draft_version=draft_version,
        )
        if plan_impact.severity != ImpactSeverity.NONE:
            affected_plans.append(plan_impact)
            if plan_impact.graduation_delay_terms > 0:
                students_delayed_count += 1

    # 6. Quantitative Summary
    summary = ImpactSummary(
        total_students_assessed=len(active_students),
        total_students_affected=len(affected_students),
        total_plans_assessed=len(active_plans),
        total_plans_affected=len(affected_plans),
        students_delayed_count=students_delayed_count,
        high_impact_count=high_impact_count,
        moderate_impact_count=moderate_impact_count,
        low_impact_count=low_impact_count,
    )

    return CurriculumImpactReport(
        draft_version_id=str(draft_version.id),
        draft_version_number=draft_version.version_number,
        published_version_id=str(published_version.id),
        published_version_number=published_version.version_number,
        programme_code=programme.code,
        programme_name=programme.name,
        summary=summary,
        requirement_changes=requirement_diffs,
        prerequisite_changes=prerequisite_diffs,
        affected_students=affected_students,
        affected_plans=affected_plans,
        analyzed_at=timezone.now().isoformat(),
    )


def _compute_requirement_diffs(
    pub_ver: CurriculumVersion,
    draft_ver: CurriculumVersion,
) -> list[RequirementDiff]:
    """Compares requirement groups and mandatory course memberships between versions."""
    diffs: list[RequirementDiff] = []

    pub_groups = {g.name.strip(): g for g in pub_ver.requirement_groups.all()}
    draft_groups = {g.name.strip(): g for g in draft_ver.requirement_groups.all()}

    # Check for modified or unchanged groups
    for name, d_grp in draft_groups.items():
        if name in pub_groups:
            p_grp = pub_groups[name]

            p_mandatory = set(
                RequirementGroupCourse.objects.filter(
                    requirement_group=p_grp, is_mandatory=True
                ).values_list("course__code", flat=True)
            )
            d_mandatory = set(
                RequirementGroupCourse.objects.filter(
                    requirement_group=d_grp, is_mandatory=True
                ).values_list("course__code", flat=True)
            )

            added_courses = sorted(list(d_mandatory - p_mandatory))
            removed_courses = sorted(list(p_mandatory - d_mandatory))

            credits_changed = p_grp.min_credits != d_grp.min_credits
            courses_changed = p_grp.min_courses != d_grp.min_courses

            if credits_changed or courses_changed or added_courses or removed_courses:
                desc_parts = []
                if credits_changed:
                    desc_parts.append(
                        f"Min credits changed: {p_grp.min_credits} -> {d_grp.min_credits}"
                    )
                if courses_changed:
                    desc_parts.append(
                        f"Min courses changed: {p_grp.min_courses} -> {d_grp.min_courses}"
                    )
                if added_courses:
                    desc_parts.append(f"Added mandatory: {', '.join(added_courses)}")
                if removed_courses:
                    desc_parts.append(f"Removed mandatory: {', '.join(removed_courses)}")

                diffs.append(
                    RequirementDiff(
                        group_id=str(d_grp.id),
                        group_name=name,
                        change_type="MODIFIED",
                        old_min_credits=float(p_grp.min_credits),
                        new_min_credits=float(d_grp.min_credits),
                        old_min_courses=p_grp.min_courses,
                        new_min_courses=d_grp.min_courses,
                        added_mandatory_courses=added_courses,
                        removed_mandatory_courses=removed_courses,
                        description="; ".join(desc_parts),
                    )
                )
        else:
            # Group added in draft
            added_mandatory = sorted(
                list(
                    RequirementGroupCourse.objects.filter(
                        requirement_group=d_grp, is_mandatory=True
                    ).values_list("course__code", flat=True)
                )
            )
            diffs.append(
                RequirementDiff(
                    group_id=str(d_grp.id),
                    group_name=name,
                    change_type="ADDED",
                    new_min_credits=float(d_grp.min_credits),
                    new_min_courses=d_grp.min_courses,
                    added_mandatory_courses=added_mandatory,
                    description=f"New requirement group added with {d_grp.min_credits} min credits.",
                )
            )

    # Check for groups removed from published
    for name, p_grp in pub_groups.items():
        if name not in draft_groups:
            removed_mandatory = sorted(
                list(
                    RequirementGroupCourse.objects.filter(
                        requirement_group=p_grp, is_mandatory=True
                    ).values_list("course__code", flat=True)
                )
            )
            diffs.append(
                RequirementDiff(
                    group_id=str(p_grp.id),
                    group_name=name,
                    change_type="REMOVED",
                    old_min_credits=float(p_grp.min_credits),
                    old_min_courses=p_grp.min_courses,
                    removed_mandatory_courses=removed_mandatory,
                    description="Requirement group removed from curriculum.",
                )
            )


    return diffs


def _compute_prerequisite_diffs(
    pub_ver: CurriculumVersion,
    draft_ver: CurriculumVersion,
) -> list[PrerequisiteChange]:
    """Compares prerequisite rules between published and draft curriculum versions."""
    diffs: list[PrerequisiteChange] = []

    pub_rules = {
        r.course.code.upper(): r
        for r in PrerequisiteRule.objects.filter(curriculum_version=pub_ver).select_related("course")
    }
    draft_rules = {
        r.course.code.upper(): r
        for r in PrerequisiteRule.objects.filter(curriculum_version=draft_ver).select_related("course")
    }

    all_course_codes = sorted(list(set(pub_rules.keys()) | set(draft_rules.keys())))

    for code in all_course_codes:
        p_rule = pub_rules.get(code)
        d_rule = draft_rules.get(code)

        if p_rule and d_rule:
            if p_rule.rule_json != d_rule.rule_json:
                old_sum = _summarize_ast(p_rule.rule_json)
                new_sum = _summarize_ast(d_rule.rule_json)
                diffs.append(
                    PrerequisiteChange(
                        course_code=code,
                        course_title=d_rule.course.title,
                        change_type="MODIFIED",
                        old_rule_summary=old_sum,
                        new_rule_summary=new_sum,
                        description=f"Rule updated from '{old_sum}' to '{new_sum}'.",
                    )
                )
        elif d_rule and not p_rule:
            new_sum = _summarize_ast(d_rule.rule_json)
            diffs.append(
                PrerequisiteChange(
                    course_code=code,
                    course_title=d_rule.course.title,
                    change_type="ADDED",
                    new_rule_summary=new_sum,
                    description=f"New prerequisite rule added: '{new_sum}'.",
                )
            )
        elif p_rule and not d_rule:
            old_sum = _summarize_ast(p_rule.rule_json)
            diffs.append(
                PrerequisiteChange(
                    course_code=code,
                    course_title=p_rule.course.title,
                    change_type="REMOVED",
                    old_rule_summary=old_sum,
                    description=f"Prerequisite rule removed (was '{old_sum}').",
                )
            )

    return diffs


def _evaluate_student_impact(
    student: StudentRecord,
    published_version: CurriculumVersion,
    draft_version: CurriculumVersion,
    changed_rule_courses: dict[str, PrerequisiteChange],
) -> StudentImpactDetail:
    """
    Evaluates degree audit progression differences and prerequisite eligibility
    changes for an active student under the draft curriculum version.
    """
    # 1. Degree audit against both versions
    base_audit = run_degree_audit(student, target_curriculum=published_version, is_simulation=True)
    draft_audit = run_degree_audit(student, target_curriculum=draft_version, is_simulation=True)

    reasons: list[str] = []
    severity = ImpactSeverity.NONE

    # Check overall degree satisfaction loss
    degree_lost = base_audit.is_degree_satisfied and not draft_audit.is_degree_satisfied
    if degree_lost:
        severity = ImpactSeverity.HIGH
        reasons.append("Student loses degree completion satisfaction under draft curriculum.")

    # Check remaining credits increase
    credits_diff = float(max(Decimal("0.00"), draft_audit.remaining_credits_required - base_audit.remaining_credits_required))
    if credits_diff > 0.0:
        reasons.append(f"Remaining required credits increase by {credits_diff:.1f} credits.")
        if credits_diff >= 6.0 and severity != ImpactSeverity.HIGH:
            severity = ImpactSeverity.HIGH
        elif severity == ImpactSeverity.NONE:
            severity = ImpactSeverity.MODERATE

    # Check newly unmet requirement groups
    base_satisfied_groups = {g.name for g in base_audit.groups if g.is_satisfied}
    newly_unmet_groups: list[str] = []

    for d_group in draft_audit.groups:
        if not d_group.is_satisfied:
            if d_group.name in base_satisfied_groups:
                newly_unmet_groups.append(d_group.name)
                reasons.append(f"Requirement group '{d_group.name}' is satisfied in published version but unmet in draft.")
            elif d_group.name not in {g.name for g in base_audit.groups}:
                newly_unmet_groups.append(d_group.name)
                reasons.append(f"New requirement group '{d_group.name}' is unmet in draft curriculum.")

    if newly_unmet_groups and severity == ImpactSeverity.NONE:
        severity = ImpactSeverity.MODERATE

    # 2. Check prerequisite eligibility changes
    ineligible_courses: list[str] = []
    if changed_rule_courses:
        rule_context = build_rule_context(student)
        for code, change in changed_rule_courses.items():
            # Check if student completed course already
            if code in rule_context.completed_courses:
                continue

            old_rule = PrerequisiteRule.objects.filter(
                curriculum_version=published_version, course__code=code
            ).first()
            new_rule = PrerequisiteRule.objects.filter(
                curriculum_version=draft_version, course__code=code
            ).first()

            old_eligible = True
            if old_rule and old_rule.rule_json:
                old_res = evaluate_rule(old_rule.rule_json, rule_context)
                old_eligible = old_res.eligible

            new_eligible = True
            if new_rule and new_rule.rule_json:
                new_res = evaluate_rule(new_rule.rule_json, rule_context)
                new_eligible = new_res.eligible

            if old_eligible and not new_eligible:
                ineligible_courses.append(code)
                reasons.append(f"Student loses prerequisite eligibility for {code} under draft rules.")
                if severity == ImpactSeverity.NONE:
                    severity = ImpactSeverity.MODERATE

    student_name = f"{student.student.first_name} {student.student.last_name}".strip() or student.student.username

    return StudentImpactDetail(
        student_id=str(student.id),
        student_username=student.student.username,
        student_name=student_name,
        severity=severity,
        is_degree_satisfaction_lost=degree_lost,
        remaining_credits_increase=credits_diff,
        newly_unmet_groups=newly_unmet_groups,
        prerequisite_ineligibilities=ineligible_courses,
        reasons=reasons,
    )


def _evaluate_plan_impact(
    plan: Plan,
    published_version: CurriculumVersion,
    draft_version: CurriculumVersion,
) -> PlanImpactDetail:
    """
    Simulates a multi-semester degree plan against both published and draft curricula
    to detect new hard constraint violations, offering mismatches, and timeline delays.
    """
    base_sim = simulate_plan(plan, alternative_curriculum=published_version)
    draft_sim = simulate_plan(plan, alternative_curriculum=draft_version)

    reasons: list[str] = []
    severity = ImpactSeverity.NONE

    # New hard constraints
    base_hc_sigs = {(hc.code, hc.course_code, hc.term_index) for hc in base_sim.hard_constraints}
    new_hcs = [hc for hc in draft_sim.hard_constraints if (hc.code, hc.course_code, hc.term_index) not in base_hc_sigs]
    new_hc_messages = [f"{hc.code}: {hc.message}" for hc in new_hcs]

    if new_hcs:
        severity = ImpactSeverity.HIGH
        reasons.append(f"Plan incurs {len(new_hcs)} new hard constraint violation(s) under draft curriculum.")

    # Offering conflicts
    base_off_sigs = {
        (w.code, w.course_code, w.term_index)
        for w in base_sim.warnings
        if w.code == "COURSE_NOT_OFFERED_IN_TERM"
    }
    new_offs = [
        w
        for w in draft_sim.warnings
        if w.code == "COURSE_NOT_OFFERED_IN_TERM"
        and (w.code, w.course_code, w.term_index) not in base_off_sigs
    ]
    new_off_messages = [w.message for w in new_offs]

    if new_offs:
        if severity == ImpactSeverity.NONE:
            severity = ImpactSeverity.MODERATE
        reasons.append(f"Plan incurs {len(new_offs)} new course offering conflict(s).")

    # Graduation delay comparison
    grad_delayed_terms = 0
    old_grad = base_sim.projected_graduation_term
    new_grad = draft_sim.projected_graduation_term

    if old_grad and new_grad and old_grad != new_grad:
        # Check if terms can be compared or shifted
        grad_delayed_terms = 1
        severity = ImpactSeverity.HIGH
        reasons.append(f"Projected graduation shifted from {old_grad} to {new_grad}.")
    elif old_grad and not new_grad and new_hcs:
        grad_delayed_terms = 1
        severity = ImpactSeverity.HIGH
        reasons.append(f"Graduation projection invalidated (was {old_grad}) due to hard constraint violations.")

    return PlanImpactDetail(
        plan_id=str(plan.id),
        plan_name=plan.name,
        student_username=plan.student_record.student.username,
        severity=severity,
        graduation_delay_terms=grad_delayed_terms,
        old_projected_grad_term=old_grad,
        new_projected_grad_term=new_grad,
        new_hard_constraints_count=len(new_hcs),
        new_hard_constraint_messages=new_hc_messages,
        offering_conflicts_count=len(new_offs),
        offering_conflict_messages=new_off_messages,
        reasons=reasons,
    )


def _summarize_ast(node: Any) -> str:
    """Generates a concise, human-readable summary of a prerequisite rule AST."""
    if not isinstance(node, dict):
        return "Unknown Rule"

    if "root" in node and isinstance(node["root"], dict):
        node = node["root"]

    node_type = node.get("type")

    if node_type == "course_completed":

        code = node.get("course_code", "")
        grade = node.get("min_grade")
        return f"{code} (min {grade})" if grade else f"{code}"

    if node_type == "corequisite":
        return f"Co-req: {node.get('course_code', '')}"

    if node_type == "anti_requisite":
        return f"Anti-req: {node.get('course_code', '')}"

    if node_type == "min_cgpa":
        return f"Min CGPA: {node.get('min_cgpa', '')}"

    if node_type == "min_credits":
        return f"Min Credits: {node.get('min_credits', '')}"

    if node_type in ("all_of", "any_of"):
        conds = node.get("conditions", [])
        op = "AND" if node_type == "all_of" else "OR"
        summaries = [_summarize_ast(c) for c in conds if isinstance(c, dict)]
        return f"({f' {op} '.join(summaries)})"

    return node_type or "Rule"
