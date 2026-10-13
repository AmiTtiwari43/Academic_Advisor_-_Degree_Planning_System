import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import InstitutionMembership, Role
from accounts.permissions import can_manage_curriculum, get_user_roles_for_institution
from curriculum.models import (
    Course,
    CourseOffering,
    CreditCategory,
    CurriculumImmutabilityError,
    CurriculumStatus,
    CurriculumVersion,
    PrerequisiteRule,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    StudentCurriculumAssignment,
)
from curriculum.serializers import (
    CourseOfferingSerializer,
    CourseSerializer,
    CreditCategorySerializer,
    CurriculumVersionSerializer,
    CurriculumVersionSummarySerializer,
    PrerequisiteRuleSerializer,
    ProgrammeSerializer,
    RequirementGroupCourseSerializer,
    RequirementGroupSerializer,
    StudentCurriculumAssignmentSerializer,
)
from curriculum.services import (
    assign_student_to_curriculum,
    clone_curriculum_version,
    compare_curriculum_versions,
    execute_rule_harness,
    get_publish_preview,
    publish_curriculum_version,
    validate_curriculum_version,
)
from institutions.models import Institution


def get_user_institutions(user: User):
    return InstitutionMembership.objects.filter(user=user, is_active=True).values_list(
        "institution_id", flat=True
    )


def get_target_institution(request, obj=None) -> Institution | None:
    if obj and hasattr(obj, "institution"):
        return obj.institution

    inst_id = (
        request.headers.get("X-Institution-ID")
        or request.query_params.get("institution_id")
        or (request.data.get("institution") if isinstance(request.data, dict) else None)
    )
    if inst_id:
        try:
            return Institution.objects.get(id=inst_id)
        except (Institution.DoesNotExist, ValueError):
            return None

    membership = (
        InstitutionMembership.objects.filter(user=request.user, is_active=True)
        .select_related("institution")
        .first()
    )
    return membership.institution if membership else None


class BaseTenantViewSet(viewsets.ModelViewSet):
    """
    Base viewset enforcing multi-tenant queryset scoping and coordinator mutation permissions.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_insts = get_user_institutions(self.request.user)
        return self.queryset.filter(institution_id__in=user_insts)

    def perform_create(self, serializer):
        institution = get_target_institution(self.request)
        if not institution:
            raise DRFValidationError("Institution context could not be determined.")
        if not can_manage_curriculum(self.request.user, institution):
            raise permissions.exceptions.PermissionDenied(
                "You do not have permission to modify curriculum data for this institution."
            )
        serializer.save(institution=institution)

    def check_mutation_permission(self, instance):
        if not can_manage_curriculum(self.request.user, instance.institution):
            raise permissions.exceptions.PermissionDenied(
                "You do not have permission to modify curriculum data for this institution."
            )


class ProgrammeViewSet(BaseTenantViewSet):
    queryset = Programme.objects.all().prefetch_related("curriculum_versions")
    serializer_class = ProgrammeSerializer

    def perform_update(self, serializer):
        self.check_mutation_permission(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_mutation_permission(instance)
        instance.delete()

    @action(detail=True, methods=["get", "post"])
    def versions(self, request, pk=None):
        programme = self.get_object()
        if request.method == "GET":
            versions = programme.curriculum_versions.all()
            return Response(CurriculumVersionSummarySerializer(versions, many=True).data)

        # POST: create new draft version
        self.check_mutation_permission(programme)
        academic_year = request.data.get("academic_year", "2026-2027")
        credits_req = request.data.get("total_credits_required", 120.00)
        cgpa_req = request.data.get("min_cgpa_required", 2.000)

        max_v = (
            programme.curriculum_versions.order_by("-version_number")
            .values_list("version_number", flat=True)
            .first()
            or 0
        )
        new_v = CurriculumVersion.objects.create(
            institution=programme.institution,
            programme=programme,
            version_number=max_v + 1,
            academic_year=academic_year,
            status=CurriculumStatus.DRAFT,
            total_credits_required=credits_req,
            min_cgpa_required=cgpa_req,
        )
        return Response(
            CurriculumVersionSerializer(new_v).data,
            status=status.HTTP_201_CREATED,
        )


class CurriculumVersionViewSet(BaseTenantViewSet):
    queryset = (
        CurriculumVersion.objects.all()
        .select_related("programme", "published_by")
        .prefetch_related(
            "requirement_groups__group_courses__course",
            "prerequisite_rules__course",
        )
    )
    serializer_class = CurriculumVersionSerializer

    def perform_update(self, serializer):
        self.check_mutation_permission(serializer.instance)
        if not serializer.instance.is_editable:
            raise DRFValidationError(
                "Published or archived curriculum versions are immutable and cannot be updated."
            )
        try:
            serializer.save()
        except (CurriculumImmutabilityError, DjangoValidationError) as exc:
            raise DRFValidationError(str(exc)) from exc

    def perform_destroy(self, instance):
        self.check_mutation_permission(instance)
        if not instance.is_editable:
            raise DRFValidationError(
                "Published or archived curriculum versions are immutable and cannot be deleted."
            )
        try:
            instance.delete()
        except (CurriculumImmutabilityError, DjangoValidationError) as exc:
            raise DRFValidationError(str(exc)) from exc

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        version = self.get_object()
        preview_data = get_publish_preview(version)
        return Response(preview_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"])
    def validate(self, request, pk=None):
        version = self.get_object()
        report = validate_curriculum_version(version)
        return Response(report.to_dict(), status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        version = self.get_object()
        self.check_mutation_permission(version)
        try:
            published_v = publish_curriculum_version(version, request.user)
            return Response(
                CurriculumVersionSerializer(published_v).data,
                status=status.HTTP_200_OK,
            )
        except (DRFValidationError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc.message if hasattr(exc, "message") else exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        version = self.get_object()
        self.check_mutation_permission(version)
        target_year = request.data.get("academic_year")
        cloned_v = clone_curriculum_version(version, request.user, target_year)
        return Response(
            CurriculumVersionSerializer(cloned_v).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="other_id",
                type=uuid.UUID,
                location=OpenApiParameter.PATH,
                description="ID of the second curriculum version to compare with",
            )
        ],
        description="Compare two curriculum versions.",
    )
    @action(detail=True, methods=["get"], url_path="diff/(?P<other_id>[^/.]+)")
    def diff(self, request, pk=None, other_id=None):
        version = self.get_object()
        user_insts = get_user_institutions(request.user)
        other_version = CurriculumVersion.objects.filter(
            id=other_id, institution_id__in=user_insts
        ).first()
        if not other_version:
            return Response(
                {"detail": "Comparison version not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        diff_data = compare_curriculum_versions(version, other_version)
        return Response(diff_data, status=status.HTTP_200_OK)


class CourseViewSet(BaseTenantViewSet):
    queryset = Course.objects.all().select_related("default_credit_category")
    serializer_class = CourseSerializer

    def perform_update(self, serializer):
        self.check_mutation_permission(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_mutation_permission(instance)
        instance.delete()


class CreditCategoryViewSet(BaseTenantViewSet):
    queryset = CreditCategory.objects.all()
    serializer_class = CreditCategorySerializer

    def perform_update(self, serializer):
        self.check_mutation_permission(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_mutation_permission(instance)
        instance.delete()


class RequirementGroupViewSet(BaseTenantViewSet):
    queryset = RequirementGroup.objects.all().prefetch_related("group_courses__course", "children")
    serializer_class = RequirementGroupSerializer

    def perform_create(self, serializer):
        curriculum_version_id = self.request.data.get("curriculum_version")
        version = CurriculumVersion.objects.get(id=curriculum_version_id)
        if not version.is_editable:
            raise DRFValidationError(
                "Cannot add requirement groups to a published curriculum version."
            )
        self.check_mutation_permission(version)
        serializer.save(institution=version.institution)

    def perform_update(self, serializer):
        group = serializer.instance
        if not group.curriculum_version.is_editable:
            raise DRFValidationError(
                "Cannot modify requirement groups of a published curriculum version."
            )
        self.check_mutation_permission(group)
        serializer.save()

    def perform_destroy(self, instance):
        if not instance.curriculum_version.is_editable:
            raise DRFValidationError(
                "Cannot delete requirement groups of a published curriculum version."
            )
        self.check_mutation_permission(instance)
        instance.delete()

    @action(detail=True, methods=["post"])
    def add_course(self, request, pk=None):
        group = self.get_object()
        if not group.curriculum_version.is_editable:
            return Response(
                {"detail": "Cannot modify published curriculum version."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.check_mutation_permission(group)
        course_id = request.data.get("course_id")
        is_mandatory = request.data.get("is_mandatory", True)
        display_order = request.data.get("display_order", 0)

        course = Course.objects.filter(id=course_id, institution=group.institution).first()
        if not course:
            return Response(
                {"detail": "Course not found in this institution."},
                status=status.HTTP_404_NOT_FOUND,
            )

        rgc, _ = RequirementGroupCourse.objects.get_or_create(
            requirement_group=group,
            course=course,
            defaults={
                "is_mandatory": is_mandatory,
                "display_order": display_order,
            },
        )
        return Response(
            RequirementGroupCourseSerializer(rgc).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def remove_course(self, request, pk=None):
        group = self.get_object()
        if not group.curriculum_version.is_editable:
            return Response(
                {"detail": "Cannot modify published curriculum version."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.check_mutation_permission(group)
        course_id = request.data.get("course_id")
        deleted_count, _ = RequirementGroupCourse.objects.filter(
            requirement_group=group, course_id=course_id
        ).delete()
        if deleted_count == 0:
            return Response(
                {"detail": "Course assignment not found in this group."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"detail": "Course removed from requirement group."},
            status=status.HTTP_200_OK,
        )


class PrerequisiteRuleViewSet(BaseTenantViewSet):
    queryset = PrerequisiteRule.objects.all().select_related("curriculum_version", "course")
    serializer_class = PrerequisiteRuleSerializer

    def perform_create(self, serializer):
        version_id = self.request.data.get("curriculum_version")
        version = CurriculumVersion.objects.get(id=version_id)
        if not version.is_editable:
            raise DRFValidationError(
                "Cannot add prerequisite rules to a published curriculum version."
            )
        self.check_mutation_permission(version)
        serializer.save(institution=version.institution)

    def perform_update(self, serializer):
        rule = serializer.instance
        if not rule.curriculum_version.is_editable:
            raise DRFValidationError(
                "Cannot modify prerequisite rules of a published curriculum version."
            )
        self.check_mutation_permission(rule)
        serializer.save()

    def perform_destroy(self, instance):
        if not instance.curriculum_version.is_editable:
            raise DRFValidationError(
                "Cannot delete prerequisite rules of a published curriculum version."
            )
        self.check_mutation_permission(instance)
        instance.delete()


class CourseOfferingViewSet(BaseTenantViewSet):
    queryset = CourseOffering.objects.all().select_related("course")
    serializer_class = CourseOfferingSerializer

    def perform_update(self, serializer):
        self.check_mutation_permission(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_mutation_permission(instance)
        instance.delete()


class StudentCurriculumAssignmentViewSet(BaseTenantViewSet):
    queryset = StudentCurriculumAssignment.objects.all().select_related(
        "student", "curriculum_version__programme", "assigned_by"
    )
    serializer_class = StudentCurriculumAssignmentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Students can only view their own assignments
        user_roles = get_user_roles_for_institution(
            self.request.user, get_target_institution(self.request)
        )
        if Role.STUDENT in user_roles and not any(
            r in user_roles for r in [Role.COORDINATOR, Role.ADVISOR, Role.HOD, Role.ADMIN]
        ):
            return qs.filter(student=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        student_id = request.data.get("student")
        version_id = request.data.get("curriculum_version")

        user_insts = get_user_institutions(request.user)
        version = CurriculumVersion.objects.filter(
            id=version_id, institution_id__in=user_insts
        ).first()
        if not version:
            return Response(
                {"detail": "Curriculum version not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        student = User.objects.filter(id=student_id).first()
        if not student:
            return Response(
                {"detail": "Student user not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Coordinator or Advisor permission required to assign
        roles = get_user_roles_for_institution(request.user, version.institution)
        if not any(r in roles for r in [Role.COORDINATOR, Role.ADVISOR, Role.HOD, Role.ADMIN]):
            return Response(
                {"detail": "Permission denied to assign students to curriculum."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            assignment = assign_student_to_curriculum(
                student=student,
                curriculum_version=version,
                assigned_by=request.user,
            )
            return Response(
                StudentCurriculumAssignmentSerializer(assignment).data,
                status=status.HTTP_201_CREATED,
            )
        except (DRFValidationError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc.message if hasattr(exc, "message") else exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RuleTestHarnessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=dict,
        responses={200: dict, 400: dict},
        description="Test a draft prerequisite rule against a hypothetical student context.",
    )
    def post(self, request):
        rule_json = request.data.get("rule_json")
        context_payload = request.data.get("context", {})

        if not rule_json:
            return Response(
                {"detail": "rule_json field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = execute_rule_harness(rule_json, context_payload)
            return Response(result, status=status.HTTP_200_OK)
        except (DRFValidationError, DjangoValidationError) as exc:
            return Response(
                {"detail": str(exc.message if hasattr(exc, "message") else exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Evaluation error: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
