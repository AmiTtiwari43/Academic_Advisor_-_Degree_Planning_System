import uuid

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from academic_records.models import StudentRecord
from accounts.models import Role
from accounts.permissions import can_view_student_record, get_user_roles_for_institution
from advising.models import RiskAcknowledgment
from advising.serializers import (
    InstitutionRiskSummarySerializer,
    RiskAcknowledgmentSerializer,
    RiskEvaluationResultSerializer,
)
from advising.services.risk_service import (
    evaluate_student_risks,
    get_institution_risk_summary,
    get_student_risk_profile,
)
from institutions.models import Institution
from planning.models import Plan


def _get_active_institution(request: Request, institution_id: str | None = None) -> Institution:
    """Helper to resolve and validate the request institution context."""
    user = request.user
    if institution_id:
        return get_object_or_404(Institution, id=institution_id)

    header_inst = request.headers.get("X-Institution-ID")
    if header_inst:
        try:
            return get_object_or_404(Institution, id=header_inst)
        except (ValueError, ValidationError):  # noqa: F821
            pass

    membership = user.institution_memberships.filter(is_active=True).first()
    if membership:
        return membership.institution

    raise PermissionDenied("Active institutional context required.")


class StudentRiskProfileView(APIView):
    """
    Fetches transparent rule-based academic risk indicators for a student.
    - Students can access only their own risk profile.
    - Faculty advisors can access assigned advisees.
    - Coordinators and Admins can access all students within their institution.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RiskEvaluationResultSerializer

    @extend_schema(
        summary="Get Student Academic Risk Profile",
        description="Returns deterministic rule-based academic risk indicators with contributing factors.",
        parameters=[
            OpenApiParameter(
                name="refresh",
                type=bool,
                required=False,
                description="Force live re-evaluation of all transparent risk rules.",
            ),
        ],
        responses={200: RiskEvaluationResultSerializer, 403: dict, 404: dict},
    )
    def get(self, request: Request, student_id: str) -> Response:
        institution = _get_active_institution(request)
        student_record = get_object_or_404(
            StudentRecord.objects.select_related("student", "programme", "pinned_curriculum"),
            id=student_id,
            institution=institution,
        )

        if not can_view_student_record(request.user, student_record.student, institution):
            raise PermissionDenied("You do not have permission to view this student's risk profile.")

        refresh = request.query_params.get("refresh", "false").lower() in ("true", "1", "yes")
        result = get_student_risk_profile(student_record, refresh=refresh, user=request.user)

        serializer = RiskEvaluationResultSerializer(result.to_dict())
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentRiskEvaluateView(APIView):
    """
    Triggers immediate re-evaluation of transparent academic risk rules for a student.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RiskEvaluationResultSerializer

    @extend_schema(
        summary="Evaluate Student Academic Risks",
        description="Executes all deterministic academic risk checks and updates the persistent profile.",
        request=None,
        responses={200: RiskEvaluationResultSerializer, 403: dict, 404: dict},
    )
    def post(self, request: Request, student_id: str) -> Response:
        institution = _get_active_institution(request)
        student_record = get_object_or_404(
            StudentRecord.objects.select_related("student", "programme", "pinned_curriculum"),
            id=student_id,
            institution=institution,
        )

        if not can_view_student_record(request.user, student_record.student, institution):
            raise PermissionDenied("You do not have permission to evaluate this student's risk profile.")

        result = evaluate_student_risks(student_record, save=True, assessed_by=request.user)
        serializer = RiskEvaluationResultSerializer(result.to_dict())
        return Response(serializer.data, status=status.HTTP_200_OK)


class PlanRiskView(APIView):
    """
    Evaluates academic risk indicators in the context of a specific degree plan.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RiskEvaluationResultSerializer

    @extend_schema(
        summary="Get Plan-Specific Academic Risks",
        description="Evaluates academic risks taking into account the planned terms and courses in a degree plan.",
        responses={200: RiskEvaluationResultSerializer, 403: dict, 404: dict},
    )
    def get(self, request: Request, plan_id: uuid.UUID) -> Response:
        institution = _get_active_institution(request)
        plan = get_object_or_404(
            Plan.objects.select_related("student_record__student", "student_record__programme", "curriculum_version"),
            id=plan_id,
            institution=institution,
        )

        student_record = plan.student_record
        if not can_view_student_record(request.user, student_record.student, institution):
            raise PermissionDenied("You do not have permission to view risks for this plan.")

        result = evaluate_student_risks(student_record, plan=plan, save=False, assessed_by=request.user)
        serializer = RiskEvaluationResultSerializer(result.to_dict())
        return Response(serializer.data, status=status.HTTP_200_OK)


class InstitutionRiskSummaryView(APIView):
    """
    Aggregated institution-wide risk metrics. Accessible to Advisors, Coordinators, and Admins.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InstitutionRiskSummarySerializer

    @extend_schema(
        summary="Get Institution Academic Risk Summary",
        description="Returns aggregated counts of assessed students by risk severity and category.",
        parameters=[
            OpenApiParameter(
                name="programme",
                type=str,
                required=False,
                description="Optional programme code filter (e.g. CS).",
            ),
        ],
        responses={200: InstitutionRiskSummarySerializer, 403: dict},
    )
    def get(self, request: Request) -> Response:
        institution = _get_active_institution(request)
        roles = get_user_roles_for_institution(request.user, institution)

        if not any(r in roles for r in [Role.ADVISOR, Role.COORDINATOR, Role.HOD, Role.ADMIN]):
            raise PermissionDenied("Access restricted to academic advisors, coordinators, and administrators.")

        programme_code = request.query_params.get("programme")
        summary_data = get_institution_risk_summary(institution, programme_code=programme_code)
        serializer = InstitutionRiskSummarySerializer(summary_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RiskAcknowledgmentViewSet(viewsets.ModelViewSet):
    """
    Advisor acknowledgment, action plan, and guidance notes on identified academic risks.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RiskAcknowledgmentSerializer
    queryset = RiskAcknowledgment.objects.all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return RiskAcknowledgment.objects.none()

        institution = _get_active_institution(self.request)
        roles = get_user_roles_for_institution(self.request.user, institution)

        qs = RiskAcknowledgment.objects.filter(institution=institution).select_related(
            "risk_profile__student_record__student",
            "advisor",
        )

        if Role.ADMIN in roles or Role.COORDINATOR in roles or Role.HOD in roles:
            return qs

        if Role.ADVISOR in roles:
            return qs.filter(advisor=self.request.user)

        # Students can view acknowledgments on their own risk profile
        if Role.STUDENT in roles:
            return qs.filter(risk_profile__student_record__student=self.request.user)

        return RiskAcknowledgment.objects.none()

    def perform_create(self, serializer: RiskAcknowledgmentSerializer) -> None:
        institution = _get_active_institution(self.request)
        roles = get_user_roles_for_institution(self.request.user, institution)
        if not any(r in roles for r in [Role.ADVISOR, Role.COORDINATOR, Role.HOD, Role.ADMIN]):
            raise PermissionDenied("Only advisors and coordinators can acknowledge or add notes to risks.")

        serializer.save(
            institution=institution,
            advisor=self.request.user,
        )
