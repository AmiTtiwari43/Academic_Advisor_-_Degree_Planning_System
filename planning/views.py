
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from academic_records.models import AcademicTerm, StudentRecord
from accounts.models import AdvisorAssignment, Role
from accounts.permissions import can_view_student_record, get_user_roles_for_institution
from curriculum.models import Course, CurriculumVersion
from institutions.models import Institution
from planning.models import Plan
from planning.serializers import (
    AddCoursePayloadSerializer,
    MoveCoursePayloadSerializer,
    PlanDetailSerializer,
    PlanItemSerializer,
    PlanSerializer,
    PlanUpdatePayloadSerializer,
    PlanVersionSerializer,
    RemoveCoursePayloadSerializer,
    SubmitPlanPayloadSerializer,
    WhatIfPayloadSerializer,
)
from planning.services.plan_management_service import (
    PlanConcurrencyError,
    PlanValidationError,
    add_course_to_plan,
    create_plan,
    move_course_in_plan,
    remove_course_from_plan,
    update_plan,
)
from planning.services.simulation_service import simulate_plan
from planning.services.snapshot_service import (
    compare_plan_versions,
    create_plan_version_snapshot,
)
from planning.services.what_if_service import simulate_what_if


class PlanViewSet(viewsets.ModelViewSet):
    """
    CRUD and actions for student degree plans.
    Enforces tenant scoping, ownership/advising permissions, and optimistic concurrency.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["retrieve", "update", "partial_update"]:
            return PlanDetailSerializer
        return PlanSerializer

    def _get_user_institution(self) -> Institution:
        membership = self.request.user.institution_memberships.select_related("institution").first()
        if not membership:
            raise PermissionDenied("User has no institution membership.")
        return membership.institution

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Plan.objects.none()

        inst = self._get_user_institution()
        roles = get_user_roles_for_institution(self.request.user, inst.id)

        base_qs = Plan.objects.filter(institution=inst).select_related(
            "student_record__student", "curriculum_version__programme"
        )

        if Role.STUDENT in roles:
            return base_qs.filter(student_record__student=self.request.user)

        if Role.ADVISOR in roles and Role.COORDINATOR not in roles and Role.ADMIN not in roles:
            # Advisor sees assigned advisee plans only
            assigned_student_ids = AdvisorAssignment.objects.filter(
                institution=inst,
                advisor__user=self.request.user,
                is_active=True,
            ).values_list("student__user_id", flat=True)
            return base_qs.filter(student_record__student_id__in=assigned_student_ids)

        # Coordinators and Admins see all plans within their institution
        return base_qs

    def perform_create(self, serializer):
        inst = self._get_user_institution()
        student_record_id = self.request.data.get("student_record")
        if not student_record_id:
            raise DRFValidationError({"student_record": "Student record is required."})

        student_record = StudentRecord.objects.filter(
            id=student_record_id, institution=inst
        ).first()
        if not student_record:
            raise NotFound("Student record not found in your institution.")

        # Permissions check
        if not can_view_student_record(self.request.user, student_record):
            raise PermissionDenied("You do not have permission to create a plan for this student.")

        name = self.request.data.get("name", "Primary Academic Plan")
        is_primary = self.request.data.get("is_primary", True)

        try:
            plan = create_plan(
                student_record=student_record,
                name=name,
                is_primary=is_primary,
            )
            serializer.instance = plan
        except PlanValidationError as exc:
            raise DRFValidationError({"detail": str(exc)})

    def update(self, request, *args, **kwargs):
        plan = self.get_object()
        serializer = PlanUpdatePayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        expected_row_version = serializer.validated_data["expected_row_version"]
        name = serializer.validated_data.get("name")
        is_primary = serializer.validated_data.get("is_primary")

        try:
            updated = update_plan(
                plan=plan,
                expected_row_version=expected_row_version,
                name=name,
                is_primary=is_primary,
            )
            return Response(PlanDetailSerializer(updated).data)
        except PlanConcurrencyError as exc:
            return Response(
                {"code": "CONCURRENCY_CONFLICT", "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

    @action(detail=True, methods=["post"], url_path="simulate")
    def simulate(self, request, pk=None):
        """
        Runs dry-run simulation of the plan against curriculum prerequisites, term loads,
        and degree audit requirements.
        """
        plan = self.get_object()
        report = simulate_plan(plan)
        return Response(report.to_dict(), status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        """
        Freezes current plan state into an immutable PlanVersion snapshot and transitions to SUBMITTED.
        """
        plan = self.get_object()
        serializer = SubmitPlanPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data.get("submission_note", "")

        try:
            version = create_plan_version_snapshot(
                plan=plan,
                submitted_by=request.user,
                submission_note=note,
            )
            return Response(
                PlanVersionSerializer(version).data,
                status=status.HTTP_201_CREATED,
            )
        except PlanValidationError as exc:
            return Response(
                {"code": "VALIDATION_ERROR", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="add-course")
    def add_course(self, request, pk=None):
        """
        Adds a course to a planned semester.
        """
        plan = self.get_object()
        serializer = AddCoursePayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inst = self._get_user_institution()
        course = Course.objects.filter(
            id=serializer.validated_data["course_id"], institution=inst
        ).first()
        if not course:
            raise NotFound("Course not found in institution.")

        term = AcademicTerm.objects.filter(
            id=serializer.validated_data["planned_term_id"], institution=inst
        ).first()
        if not term:
            raise NotFound("Academic term not found in institution.")

        try:
            item = add_course_to_plan(
                plan=plan,
                course=course,
                planned_term=term,
                term_index=serializer.validated_data["term_index"],
                position=serializer.validated_data.get("position"),
                expected_row_version=serializer.validated_data.get("expected_row_version"),
                notes=serializer.validated_data.get("notes", ""),
            )
            return Response(PlanItemSerializer(item).data, status=status.HTTP_201_CREATED)
        except PlanConcurrencyError as exc:
            return Response(
                {"code": "CONCURRENCY_CONFLICT", "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except PlanValidationError as exc:
            return Response(
                {"code": "VALIDATION_ERROR", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="remove-course")
    def remove_course(self, request, pk=None):
        """
        Removes a course from the plan.
        """
        plan = self.get_object()
        serializer = RemoveCoursePayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            remove_course_from_plan(
                plan=plan,
                plan_item_id=serializer.validated_data["plan_item_id"],
                expected_row_version=serializer.validated_data.get("expected_row_version"),
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PlanConcurrencyError as exc:
            return Response(
                {"code": "CONCURRENCY_CONFLICT", "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except PlanValidationError as exc:
            return Response(
                {"code": "VALIDATION_ERROR", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="move-course")
    def move_course(self, request, pk=None):
        """
        Moves or reorders a course to a different term or position.
        """
        plan = self.get_object()
        serializer = MoveCoursePayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inst = self._get_user_institution()
        term = AcademicTerm.objects.filter(
            id=serializer.validated_data["target_term_id"], institution=inst
        ).first()
        if not term:
            raise NotFound("Target academic term not found.")

        try:
            item = move_course_in_plan(
                plan=plan,
                plan_item_id=serializer.validated_data["plan_item_id"],
                target_term=term,
                target_term_index=serializer.validated_data["target_term_index"],
                target_position=serializer.validated_data.get("target_position", 0),
                expected_row_version=serializer.validated_data.get("expected_row_version"),
            )
            return Response(PlanItemSerializer(item).data, status=status.HTTP_200_OK)
        except PlanConcurrencyError as exc:
            return Response(
                {"code": "CONCURRENCY_CONFLICT", "message": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )
        except PlanValidationError as exc:
            return Response(
                {"code": "VALIDATION_ERROR", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, pk=None):
        """
        Lists historical immutable PlanVersion snapshots.
        """
        plan = self.get_object()
        versions = plan.versions.all().order_by("-version_number")
        return Response(PlanVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["get"], url_path="diff")
    def diff(self, request, pk=None):
        """
        Compares two snapshot versions (query params: v1, v2).
        """
        plan = self.get_object()
        v1_num = request.query_params.get("v1")
        v2_num = request.query_params.get("v2")

        if not v1_num or not v2_num:
            raise DRFValidationError({"detail": "Query parameters 'v1' and 'v2' are required."})

        v1 = plan.versions.filter(version_number=v1_num).first()
        v2 = plan.versions.filter(version_number=v2_num).first()

        if not v1 or not v2:
            raise NotFound("One or both requested snapshot versions not found.")

        diff_res = compare_plan_versions(v1, v2)
        return Response(diff_res, status=status.HTTP_200_OK)


class WhatIfSimulationView(GenericAPIView):
    """
    Simulates degree progress and optional plan outcomes against an alternative curriculum version.
    """
    serializer_class = WhatIfPayloadSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=WhatIfPayloadSerializer)
    def post(self, request, *args, **kwargs):
        serializer = WhatIfPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = request.user.institution_memberships.first()
        if not membership:
            raise PermissionDenied("User has no institution membership.")
        inst = membership.institution

        student_rec = StudentRecord.objects.filter(
            id=serializer.validated_data["student_record_id"],
            institution=inst,
        ).first()
        if not student_rec:
            raise NotFound("Student record not found.")

        if not can_view_student_record(request.user, student_rec):
            raise PermissionDenied("You do not have permission to view this student record.")

        target_curriculum = CurriculumVersion.objects.filter(
            id=serializer.validated_data["target_curriculum_version_id"],
            institution=inst,
        ).first()
        if not target_curriculum:
            raise NotFound("Target curriculum version not found.")

        plan = None
        plan_id = serializer.validated_data.get("plan_id")
        if plan_id:
            plan = Plan.objects.filter(id=plan_id, institution=inst).first()
            if not plan:
                raise NotFound("Specified plan not found.")

        report = simulate_what_if(
            student_record=student_rec,
            target_curriculum=target_curriculum,
            plan=plan,
        )
        return Response(report, status=status.HTTP_200_OK)
