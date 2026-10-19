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
from curriculum.models import Course, CurriculumVersion, PrerequisiteRule
from degree_audit.services.audit_service import run_degree_audit
from institutions.models import Institution


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
        ).select_related("programme", "pinned_curriculum").first()

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

    elif user_role in (Role.COORDINATOR, Role.ADMIN):
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
        "pinned_curriculum": None,
        "degree_audit": None,
        "completed_courses": [],
        "catalog_courses": [],
        "prerequisite_rules": [],
    }

    pinned_version: Optional[CurriculumVersion] = None

    if target_student_rec:
        pinned_version = target_student_rec.pinned_curriculum
        context_data["student_record"] = {
            "id": str(target_student_rec.id),
            "programme_code": target_student_rec.programme.code,
            "programme_name": target_student_rec.programme.name,
            "status": target_student_rec.status,
            "cached_cgpa": str(target_student_rec.cached_cgpa),
            "cached_total_credits": str(target_student_rec.cached_total_credits),
        }

        entries = TranscriptEntry.objects.filter(
            institution=institution,
            student_record=target_student_rec,
            status=TranscriptEntryStatus.COMPLETED,
            verification_status=VerificationStatus.VERIFIED,
        ).select_related("course")

        context_data["completed_courses"] = [
            {
                "code": e.course.code,
                "title": e.course.title,
                "credits": float(e.credits_earned or e.course.credits),
                "grade": e.grade,
                "term_code": e.term.code if e.term else "",
            }
            for e in entries
        ]

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
        catalog = Course.objects.filter(institution=institution, is_active=True)[:50]
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
