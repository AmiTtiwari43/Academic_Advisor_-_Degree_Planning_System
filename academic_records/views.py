import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from academic_records.models import (
    AcademicTerm,
    Exemption,
    StudentRecord,
    TranscriptEntry,
    TransferCredit,
)
from academic_records.serializers import (
    AcademicTermSerializer,
    ExemptionSerializer,
    StudentRecordDetailSerializer,
    StudentRecordSerializer,
    TranscriptEntrySerializer,
    TransferCreditSerializer,
)
from accounts.models import AdvisorAssignment, InstitutionMembership, Role
from accounts.permissions import (
    can_manage_curriculum,
    can_view_student_record,
)
from curriculum.models import Course
from degree_audit.services import run_degree_audit
from eligibility.services import check_course_eligibility


def get_user_institutions(user: User):
    return InstitutionMembership.objects.filter(
        user=user, is_active=True
    ).values_list("institution_id", flat=True)


class BaseTenantViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        if user.is_superuser:
            return self.queryset
        inst_ids = get_user_institutions(user)
        return self.queryset.filter(institution_id__in=inst_ids)


class AcademicTermViewSet(BaseTenantViewSet):
    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer

    def perform_create(self, serializer):
        user = self.request.user
        inst_id = self.request.data.get("institution")
        if not inst_id:
            membership = InstitutionMembership.objects.filter(user=user, is_active=True).first()
            if not membership:
                raise DRFValidationError("User has no active institutional membership.")
            inst = membership.institution
        else:
            inst = InstitutionMembership.objects.filter(
                user=user, institution_id=inst_id, is_active=True
            ).values("institution").first()
            if not inst and not user.is_superuser:
                raise PermissionDenied("User is not an active member of this institution.")
            inst = serializer.validated_data["institution"]

        if not can_manage_curriculum(user, inst):
            raise PermissionDenied("Only academic coordinators and administrators can create academic terms.")
        serializer.save(institution=inst)


class StudentRecordViewSet(BaseTenantViewSet):
    queryset = StudentRecord.objects.all().select_related(
        "student",
        "programme",
        "pinned_curriculum",
        "enrollment_term",
        "expected_graduation_term",
    )
    serializer_class = StudentRecordSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return StudentRecordDetailSerializer
        return StudentRecordSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        if user.is_superuser:
            return self.queryset

        memberships = list(
            InstitutionMembership.objects.filter(user=user, is_active=True).select_related("institution")
        )
        if not memberships:
            return self.queryset.none()

        inst_ids = [m.institution_id for m in memberships]
        base_qs = self.queryset.filter(institution_id__in=inst_ids)

        # Check if user has staff/coordinator/admin role in any membership
        is_coordinator_or_admin = any(
            m.role in [Role.COORDINATOR, Role.HOD, Role.ADMIN] for m in memberships
        )
        if is_coordinator_or_admin:
            return base_qs

        # Check if user is an advisor
        is_advisor = any(m.role == Role.ADVISOR for m in memberships)
        if is_advisor:
            advisee_student_ids = AdvisorAssignment.objects.filter(
                advisor__user=user,
                is_active=True,
            ).values_list("student__user_id", flat=True)
            return base_qs.filter(student_id__in=advisee_student_ids)

        # Default student role: only own record
        return base_qs.filter(student=user)

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if not can_view_student_record(request.user, obj.student, obj.institution):
            raise PermissionDenied("You do not have authorization to view this student record.")

    @extend_schema(summary="Run authoritative degree audit against pinned curriculum")
    @action(detail=True, methods=["get"])
    def audit(self, request, pk=None):
        student_record = self.get_object()
        report = run_degree_audit(student_record)
        return Response(report.to_dict(), status=status.HTTP_200_OK)

    @extend_schema(
        summary="Check course eligibility using pure-Python prerequisite engine",
        parameters=[
            OpenApiParameter("course_id", type=uuid.UUID, location=OpenApiParameter.PATH),
        ],
    )
    @action(detail=True, methods=["get"], url_path="eligibility/(?P<course_id>[^/.]+)")
    def eligibility(self, request, pk=None, course_id=None):
        student_record = self.get_object()
        course = Course.objects.filter(
            id=course_id,
            institution=student_record.institution,
        ).first()
        if not course:
            return Response(
                {"detail": "Course not found within this institution."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = check_course_eligibility(student_record, course)
        return Response(result.to_dict(), status=status.HTTP_200_OK)

    @extend_schema(summary="Retrieve all transcript entries for this student record")
    @action(detail=True, methods=["get"])
    def transcript(self, request, pk=None):
        student_record = self.get_object()
        entries = student_record.transcript_entries.select_related("course", "term").all()
        serializer = TranscriptEntrySerializer(entries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TranscriptEntryViewSet(BaseTenantViewSet):
    queryset = TranscriptEntry.objects.all().select_related("course", "term", "student_record")
    serializer_class = TranscriptEntrySerializer

    def perform_create(self, serializer):
        user = self.request.user
        rec = serializer.validated_data["student_record"]
        if not can_manage_curriculum(user, rec.institution):
            raise PermissionDenied("Only authorized academic administrators can record transcript entries.")
        try:
            serializer.save(institution=rec.institution)
        except DjangoValidationError as e:
            raise DRFValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))


class TransferCreditViewSet(BaseTenantViewSet):
    queryset = TransferCredit.objects.all().select_related("student_record")
    serializer_class = TransferCreditSerializer

    def perform_create(self, serializer):
        user = self.request.user
        rec = serializer.validated_data["student_record"]
        if not can_manage_curriculum(user, rec.institution):
            raise PermissionDenied("Only authorized academic administrators can record transfer credits.")
        serializer.save(institution=rec.institution)


class ExemptionViewSet(BaseTenantViewSet):
    queryset = Exemption.objects.all().select_related("student_record", "course", "approved_by")
    serializer_class = ExemptionSerializer

    def perform_create(self, serializer):
        user = self.request.user
        rec = serializer.validated_data["student_record"]
        if not can_manage_curriculum(user, rec.institution):
            raise PermissionDenied("Only authorized academic administrators can grant course exemptions.")
        serializer.save(institution=rec.institution, approved_by=user)
