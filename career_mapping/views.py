"""
Views and API ViewSets for Career Objective and Skill Mapping (Prompt 08D).
Enforces strict multi-tenant isolation, role authorization, and auditability.
"""

from __future__ import annotations

import uuid

from django.contrib.auth.models import User
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from academic_records.models import StudentRecord
from accounts.models import InstitutionMembership, Role
from accounts.permissions import can_manage_curriculum, can_view_student_record
from career_mapping.models import (
    CareerObjective,
    CareerSkillRequirement,
    CourseSkillMapping,
    Skill,
    StudentCareerPreference,
)
from career_mapping.serializers import (
    CareerObjectiveSerializer,
    CareerSkillRequirementSerializer,
    CourseRecommendationSerializer,
    CourseSkillMappingSerializer,
    SkillGapReportSerializer,
    SkillSerializer,
    StudentCareerPreferenceSerializer,
)
from career_mapping.services import (
    analyze_skill_gap,
    get_career_course_recommendations,
)
from institutions.models import Institution


def get_user_institutions(user: User):
    """Returns active institution IDs associated with user."""
    return InstitutionMembership.objects.filter(user=user, is_active=True).values_list(
        "institution_id", flat=True
    )


def get_target_institution(request, obj=None) -> Institution | None:
    if obj and hasattr(obj, "institution"):
        return obj.institution
    institution_id = request.data.get("institution") or request.query_params.get("institution")
    if institution_id:
        return Institution.objects.filter(
            id=institution_id, id__in=get_user_institutions(request.user)
        ).first()
    first_inst_id = get_user_institutions(request.user).first()
    if first_inst_id:
        return Institution.objects.filter(id=first_inst_id).first()
    return None


class BaseCareerTenantViewSet(viewsets.ModelViewSet):
    """
    Base viewset enforcing tenant scoping on querysets and coordinator authorization on mutations.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_insts = get_user_institutions(self.request.user)
        return self.queryset.filter(institution_id__in=user_insts)

    def check_manage_permission(self, institution: Institution):
        if not can_manage_curriculum(self.request.user, institution):
            raise PermissionDenied(
                "You do not have permission to manage career mapping data for this institution."
            )

    def perform_create(self, serializer):
        institution = get_target_institution(self.request)
        if not institution:
            raise DRFValidationError("Institution context could not be determined.")
        self.check_manage_permission(institution)
        serializer.save(institution=institution)

    def perform_update(self, serializer):
        self.check_manage_permission(serializer.instance.institution)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_manage_permission(instance.institution)
        instance.delete()


class SkillViewSet(BaseCareerTenantViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class CareerObjectiveViewSet(BaseCareerTenantViewSet):
    queryset = CareerObjective.objects.all().prefetch_related(
        "skill_requirements__skill"
    )
    serializer_class = CareerObjectiveSerializer

    @extend_schema(
        request=CareerSkillRequirementSerializer,
        responses={201: CareerSkillRequirementSerializer},
        description="Add a skill requirement to a career objective.",
    )
    @action(detail=True, methods=["post"], url_path="skills")
    def add_skill(self, request, pk=None):
        objective = self.get_object()
        self.check_manage_permission(objective.institution)

        skill_id = request.data.get("skill")
        if not skill_id:
            return Response(
                {"detail": "Skill ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        skill = Skill.objects.filter(
            id=skill_id, institution=objective.institution
        ).first()
        if not skill:
            return Response(
                {"detail": "Skill not found in this institution."},
                status=status.HTTP_404_NOT_FOUND,
            )

        min_proficiency = request.data.get("min_proficiency", "INTERMEDIATE")
        is_critical = request.data.get("is_critical", True)
        display_order = request.data.get("display_order", 0)

        req, created = CareerSkillRequirement.objects.update_or_create(
            career_objective=objective,
            skill=skill,
            defaults={
                "min_proficiency": min_proficiency,
                "is_critical": is_critical,
                "display_order": display_order,
            },
        )
        return Response(
            CareerSkillRequirementSerializer(req).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CourseSkillMappingViewSet(BaseCareerTenantViewSet):
    queryset = CourseSkillMapping.objects.all().select_related("course", "skill")
    serializer_class = CourseSkillMappingSerializer


class StudentCareerPreferenceViewSet(viewsets.ModelViewSet):
    """
    Manages student career preferences.
    Students can view and manage their own preferences.
    Advisors and Coordinators can view preferences within their institutional scope.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentCareerPreferenceSerializer
    queryset = StudentCareerPreference.objects.all()

    def get_queryset(self):
        user = self.request.user
        if getattr(self, "swagger_fake_view", False) or not user.is_authenticated:
            return StudentCareerPreference.objects.none()

        user_insts = get_user_institutions(user)


        # Check if user has advising/coordinator roles in any tenant
        has_staff_role = InstitutionMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=[Role.ADVISOR, Role.COORDINATOR, Role.HOD, Role.ADMIN],
        ).exists()

        if has_staff_role or user.is_superuser:
            return StudentCareerPreference.objects.filter(
                institution_id__in=user_insts
            ).select_related("career_objective", "student_record__student", "target_term")

        # Regular students see only their own preferences
        return StudentCareerPreference.objects.filter(
            institution_id__in=user_insts,
            student_record__student=user,
        ).select_related("career_objective", "student_record__student", "target_term")

    def perform_create(self, serializer):
        user = self.request.user
        student_record_id = self.request.data.get("student_record")

        if not student_record_id:
            # Default to student's own record
            record = StudentRecord.objects.filter(student=user).first()
            if not record:
                raise DRFValidationError("Student record could not be resolved for current user.")
        else:
            record = StudentRecord.objects.filter(id=student_record_id).first()
            if not record:
                raise DRFValidationError("Specified student record not found.")

        # Permission check
        if not can_view_student_record(user, record.student, record.institution):
            raise PermissionDenied("You do not have permission to set preferences for this student.")

        serializer.save(
            institution=record.institution,
            student_record=record,
        )


class SkillGapAnalysisView(APIView):
    """
    Runs skill-gap analysis comparing a student's acquired coursework skills
    against target career objective competencies.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="student_id",
                type=uuid.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Optional Student Record ID (defaults to current authenticated student).",
            ),
            OpenApiParameter(
                name="objective_id",
                type=uuid.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Optional Career Objective ID (defaults to student's primary preference).",
            ),
        ],
        responses={200: SkillGapReportSerializer},
        description="Run skill-gap analysis for a student record.",
    )
    def get(self, request):
        user = request.user
        user_insts = get_user_institutions(user)

        student_id = request.query_params.get("student_id")
        if student_id:
            record = StudentRecord.objects.filter(
                id=student_id, institution_id__in=user_insts
            ).first()
            if not record:
                return Response(
                    {"detail": "Student record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            record = StudentRecord.objects.filter(
                student=user, institution_id__in=user_insts
            ).first()
            if not record:
                return Response(
                    {"detail": "No student record associated with current user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not can_view_student_record(user, record.student, record.institution):
            raise PermissionDenied("You do not have permission to view this student's skill gap.")

        objective_id = request.query_params.get("objective_id")
        objective = None
        if objective_id:
            objective = CareerObjective.objects.filter(
                id=objective_id, institution=record.institution
            ).first()
            if not objective:
                return Response(
                    {"detail": "Career objective not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        try:
            report = analyze_skill_gap(student_record=record, career_objective=objective)
        except ValueError as err:
            return Response(
                {"detail": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(SkillGapReportSerializer(report.to_dict()).data, status=status.HTTP_200_OK)


class CourseRecommendationsView(APIView):
    """
    Generates explainable, deterministically ranked course recommendations
    that address a student's career skill gap while respecting degree requirements.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="student_id",
                type=uuid.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Optional Student Record ID (defaults to current authenticated student).",
            ),
            OpenApiParameter(
                name="objective_id",
                type=uuid.UUID,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Optional Career Objective ID (defaults to student's primary preference).",
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Maximum number of recommendations to return (default 10).",
            ),
        ],
        responses={200: CourseRecommendationSerializer(many=True)},
        description="Generate career-driven course recommendations.",
    )
    def get(self, request):
        user = request.user
        user_insts = get_user_institutions(user)

        student_id = request.query_params.get("student_id")
        if student_id:
            record = StudentRecord.objects.filter(
                id=student_id, institution_id__in=user_insts
            ).first()
            if not record:
                return Response(
                    {"detail": "Student record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            record = StudentRecord.objects.filter(
                student=user, institution_id__in=user_insts
            ).first()
            if not record:
                return Response(
                    {"detail": "No student record associated with current user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not can_view_student_record(user, record.student, record.institution):
            raise PermissionDenied("You do not have permission to view recommendations for this student.")

        objective_id = request.query_params.get("objective_id")
        objective = None
        if objective_id:
            objective = CareerObjective.objects.filter(
                id=objective_id, institution=record.institution
            ).first()
            if not objective:
                return Response(
                    {"detail": "Career objective not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        limit = int(request.query_params.get("limit", 10))

        try:
            recommendations = get_career_course_recommendations(
                student_record=record,
                career_objective=objective,
                limit=limit,
            )
        except ValueError as err:
            return Response(
                {"detail": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serialized = CourseRecommendationSerializer(
            [r.to_dict() for r in recommendations], many=True
        ).data
        return Response(serialized, status=status.HTTP_200_OK)
