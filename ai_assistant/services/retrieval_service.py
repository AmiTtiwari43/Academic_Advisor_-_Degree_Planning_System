import uuid
from typing import Any, Dict, Optional

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from academic_records.models import (
    StudentRecord,
    TranscriptEntry,
    TranscriptEntryStatus,
    VerificationStatus,
)
from accounts.models import AdvisorAssignment, Role
from career_mapping.models import StudentCareerPreference
from curriculum.models import Course, CurriculumVersion, PrerequisiteRule
from degree_audit.services.audit_service import run_degree_audit
from institutions.models import Institution
from planning.models import Plan


def get_authorized_context(
    user: Any,
    institution: Institution,
    student_record_id: Optional[str | uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Retrieves academic context strictly scoped to the requesting user's authorization.
    CRITICAL: Permission filtering is enforced BEFORE any records are accessed.
    """
    membership = user.institution_memberships.filter(
        institution=institution,
        is_active=True,
    ).first()

    if not membership:
        raise PermissionDenied("User is not an active member of this institution.")

    user_role = membership.role

    # 1. Resolve authorized StudentRecord
    target_student_rec: Optional[StudentRecord] = None

    if user_role == Role.STUDENT:
        # A student may ONLY query their own record
        target_student_rec = StudentRecord.objects.filter(
            institution=institution,
            student=user,
        ).select_related("programme", "pinned_curriculum", "enrollment_term").first()

        if student_record_id:
            # If explicit ID passed, verify ownership
            if not target_student_rec or str(target_student_rec.id) != str(student_record_id):
                raise PermissionDenied("Students may not access records of other students.")

    elif user_role == Role.ADVISOR:
        if student_record_id:
            target_student_rec = get_object_or_404(
                StudentRecord,
                id=student_record_id,
                institution=institution,
            )
            # Check assignment
            is_assigned = AdvisorAssignment.objects.filter(
                institution=institution,
                advisor__user=user,
                student__user=target_student_rec.student,
                is_active=True,
            ).exists()
            if not is_assigned:
                raise PermissionDenied("Advisor is not assigned to this student.")

    elif user_role in (Role.COORDINATOR, Role.ADMIN, Role.HOD):
        if student_record_id:
            target_student_rec = get_object_or_404(
                StudentRecord,
                id=student_record_id,
                institution=institution,
            )

    # 2. Extract grounded curriculum and student state
    context_data: Dict[str, Any] = {
        "institution_code": institution.code,
        "institution_name": institution.name,
        "user_role": user_role,
        "student_record": None,
        "assigned_advisor": None,
        "pinned_curriculum": None,
        "degree_audit": None,
        "completed_courses": [],
        "in_progress_courses": [],
        "failed_courses": [],
        "withdrawn_courses": [],
        "degree_plans": [],
        "career_preferences": [],
        "catalog_courses": [],
        "prerequisite_rules": [],
    }

    pinned_version: Optional[CurriculumVersion] = None

    if target_student_rec:
        pinned_version = target_student_rec.pinned_curriculum
        stud_user = target_student_rec.student
        context_data["student_record"] = {
            "id": str(target_student_rec.id),
            "username": stud_user.username,
            "first_name": stud_user.first_name,
            "last_name": stud_user.last_name,
            "email": stud_user.email,
            "programme_code": target_student_rec.programme.code,
            "programme_name": target_student_rec.programme.name,
            "status": target_student_rec.status,
            "enrollment_term": target_student_rec.enrollment_term.code if target_student_rec.enrollment_term else "FA2024",
            "repeated_course_policy": target_student_rec.repeated_course_policy,
            "cached_cgpa": str(target_student_rec.cached_cgpa),
            "cached_total_credits": str(target_student_rec.cached_total_credits),
        }

        # Assigned Advisor lookup
        adv_assign = (
            AdvisorAssignment.objects.filter(
                institution=institution,
                student__user=stud_user,
                is_active=True,
            )
            .select_related("advisor__user")
            .first()
        )
        if adv_assign and adv_assign.advisor and adv_assign.advisor.user:
            adv_u = adv_assign.advisor.user
            name_parts = [p for p in [adv_u.first_name, adv_u.last_name] if p]
            adv_display = f"Dr. {' '.join(name_parts)}" if name_parts else f"Advisor {adv_u.username}"
            context_data["assigned_advisor"] = {
                "name": adv_display,
                "email": adv_u.email,
                "department": getattr(adv_assign.advisor, "department", "School of Computing & Engineering"),
            }

        # All transcript entries
        all_entries = TranscriptEntry.objects.filter(
            institution=institution,
            student_record=target_student_rec,
        ).select_related("course", "term")

        for e in all_entries:
            course_payload = {
                "code": e.course.code,
                "title": e.course.title,
                "credits": float(e.credits_earned or e.course.credits),
                "credits_attempted": float(e.credits_attempted or e.course.credits),
                "grade": e.grade,
                "term_code": e.term.code if e.term else "",
                "status": e.status,
                "attempt_number": e.attempt_number,
            }
            if e.status == TranscriptEntryStatus.COMPLETED and e.verification_status == VerificationStatus.VERIFIED:
                context_data["completed_courses"].append(course_payload)
            elif e.status == TranscriptEntryStatus.IN_PROGRESS:
                context_data["in_progress_courses"].append(course_payload)
            elif e.status == TranscriptEntryStatus.FAILED:
                context_data["failed_courses"].append(course_payload)
            elif e.status == TranscriptEntryStatus.WITHDRAWN:
                context_data["withdrawn_courses"].append(course_payload)

        # Degree Plans
        plans = Plan.objects.filter(
            institution=institution,
            student_record=target_student_rec,
        ).prefetch_related("items__course", "items__planned_term").order_by("-is_primary", "-updated_at")

        for plan in plans:
            items_payload = [
                {
                    "course_code": item.course.code,
                    "course_title": item.course.title,
                    "credits": float(item.course.credits),
                    "term_code": item.planned_term.code if item.planned_term else "",
                    "term_index": item.term_index,
                }
                for item in plan.items.all().order_by("term_index", "position")
            ]
            context_data["degree_plans"].append({
                "id": str(plan.id),
                "name": plan.name,
                "status": plan.status,
                "is_primary": plan.is_primary,
                "courses_count": len(items_payload),
                "planned_courses": items_payload,
            })

        # Career Preferences
        career_prefs = StudentCareerPreference.objects.filter(
            institution=institution,
            student_record=target_student_rec,
        ).select_related("career_objective").prefetch_related("career_objective__skill_requirements__skill").order_by("priority")

        for cp in career_prefs:
            skills = [
                {
                    "code": req.skill.code,
                    "name": req.skill.name,
                    "category": req.skill.category,
                    "min_proficiency": req.min_proficiency,
                    "is_critical": req.is_critical,
                }
                for req in cp.career_objective.skill_requirements.all()
            ]
            context_data["career_preferences"].append({
                "code": cp.career_objective.code,
                "title": cp.career_objective.title,
                "description": cp.career_objective.description,
                "priority": cp.priority,
                "required_skills": skills,
            })

        # Authoritative degree audit evaluation
        try:
            audit_result = run_degree_audit(target_student_rec)
            context_data["degree_audit"] = audit_result.to_dict()
        except Exception:
            context_data["degree_audit"] = None

    if pinned_version:
        context_data["pinned_curriculum"] = {
            "id": str(pinned_version.id),
            "version_number": pinned_version.version_number,
            "status": pinned_version.status,
            "programme_code": pinned_version.programme.code,
            "min_cgpa_required": str(pinned_version.min_cgpa_required),
            "total_credits_required": float(pinned_version.total_credits_required),
        }

        # Prerequisite rules for pinned version
        rules_map = {
            r.course_id: r.rule_json
            for r in PrerequisiteRule.objects.filter(
                institution=institution,
                curriculum_version=pinned_version,
            )
        }

        # Courses in pinned curriculum
        curr_courses = Course.objects.filter(
            institution=institution,
            requirement_groups__curriculum_version=pinned_version,
            is_active=True,
        ).distinct()

        context_data["catalog_courses"] = [
            {
                "code": c.code,
                "title": c.title,
                "credits": float(c.credits),
                "description": c.description,
                "prerequisite_rule": rules_map.get(c.id),
            }
            for c in curr_courses
        ]
    else:
        # General active courses for institution
        catalog = Course.objects.filter(institution=institution, is_active=True)[:60]
        general_rules_map = {
            r.course_id: r.rule_json
            for r in PrerequisiteRule.objects.filter(
                institution=institution,
                course__in=catalog,
            )
        }
        context_data["catalog_courses"] = [
            {
                "code": c.code,
                "title": c.title,
                "credits": float(c.credits),
                "description": c.description,
                "prerequisite_rule": general_rules_map.get(c.id),
            }
            for c in catalog
        ]

    return context_data
