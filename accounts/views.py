from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdvisorAssignment, InstitutionMembership, Role, UserProfile
from accounts.permissions import (
    can_assign_advisor,
    can_manage_curriculum,
    can_view_student_record,
)
from accounts.serializers import (
    AdvisorAssignmentSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserMeSerializer,
    UserProfileSerializer,
)
from accounts.services import (
    assign_advisor,
    authenticate_and_login,
    confirm_password_reset,
    logout_user,
    request_password_reset,
    update_user_profile,
)
from accounts.throttling import LoginRateThrottle, PasswordResetRateThrottle
from institutions.models import Institution


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]
    serializer_class = LoginSerializer

    @extend_schema(
        request=LoginSerializer,
        responses={200: UserMeSerializer, 400: dict},
        description="Authenticate user with username and password, starting a secure session.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = authenticate_and_login(
                request,
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
            )
            return Response(UserMeSerializer(user).data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {"detail": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: dict},
        description="Terminate current session.",
    )
    def post(self, request):
        logout_user(request)
        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


class UserMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserMeSerializer

    @extend_schema(
        responses={200: UserMeSerializer},
        description="Retrieve profile and institutional memberships of the authenticated user.",
    )
    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(
        responses={200: UserProfileSerializer},
        description="Retrieve current user profile data.",
    )
    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
        description="Update current user profile data (privileged fields ignored).",
    )
    def patch(self, request):
        serializer = UserProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = update_user_profile(
            user=request.user,
            phone_number=serializer.validated_data.get("phone_number"),
            preferred_name=serializer.validated_data.get("preferred_name"),
        )
        return Response(UserProfileSerializer(profile).data, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={200: dict},
        description="Request password reset email. Rate limited; does not leak user existence.",
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "If the account exists, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: dict, 400: dict},
        description="Confirm password reset using token and UID, terminating prior sessions.",
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_password_reset(
                uidb64=serializer.validated_data["uid"],
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
            return Response(
                {"detail": "Password has been successfully reset."},
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class StudentRecordDetailView(APIView):
    """
    Authoritative student record view demonstrating object-level authorization
    and strict multi-tenant isolation.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: dict, 403: dict, 404: dict},
        description="Retrieve student record for authorized users (returns 404 for other institutions).",
    )
    def get(self, request, student_id):
        student_membership = (
            InstitutionMembership.objects.filter(
                id=student_id,
                role=Role.STUDENT,
            )
            .select_related("institution", "user")
            .first()
        )

        if not student_membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        student_institution = student_membership.institution
        actor_in_institution = (
            request.user.is_superuser
            or InstitutionMembership.objects.filter(
                user=request.user,
                institution=student_institution,
                is_active=True,
            ).exists()
        )

        if not actor_in_institution:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not can_view_student_record(request.user, student_membership.user, student_institution):
            return Response(
                {"detail": "You do not have permission to view this student record."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "id": str(student_membership.id),
                "student_id": str(student_membership.user.id),
                "username": student_membership.user.username,
                "first_name": student_membership.user.first_name,
                "last_name": student_membership.user.last_name,
                "institution": {
                    "id": str(student_institution.id),
                    "name": student_institution.name,
                    "code": student_institution.code,
                },
            },
            status=status.HTTP_200_OK,
        )


class AdvisorAssignmentListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AdvisorAssignmentSerializer

    @extend_schema(
        responses={200: AdvisorAssignmentSerializer(many=True)},
        description="List advisor assignments for authenticated user institutions.",
    )
    def get(self, request):
        user_institutions = InstitutionMembership.objects.filter(
            user=request.user,
            is_active=True,
        ).values_list("institution_id", flat=True)

        assignments = AdvisorAssignment.objects.filter(
            institution_id__in=user_institutions
        ).select_related("advisor__user", "student__user", "institution")
        serializer = AdvisorAssignmentSerializer(assignments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AdvisorAssignmentSerializer,
        responses={201: AdvisorAssignmentSerializer, 400: dict, 403: dict},
        description="Assign a faculty advisor to a student within the institution.",
    )
    def post(self, request):
        institution_id = request.data.get("institution")
        advisor_id = request.data.get("advisor")
        student_id = request.data.get("student")

        if not institution_id or not advisor_id or not student_id:
            return Response(
                {"detail": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            institution = Institution.objects.get(id=institution_id)
            advisor = InstitutionMembership.objects.get(id=advisor_id, institution=institution)
            student = InstitutionMembership.objects.get(id=student_id, institution=institution)
        except (Institution.DoesNotExist, InstitutionMembership.DoesNotExist):
            return Response({"detail": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

        if not can_assign_advisor(request.user, institution):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        try:
            assignment = assign_advisor(institution, advisor, student)
            return Response(
                AdvisorAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e.message if hasattr(e, "message") else e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CurriculumManageTestStubView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: dict, 403: dict, 404: dict},
        description="Stub endpoint testing curriculum management authorization.",
    )
    def post(self, request):
        institution_id = request.data.get("institution_id") or request.query_params.get(
            "institution_id"
        )
        if not institution_id:
            return Response(
                {"detail": "institution_id required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            institution = Institution.objects.get(id=institution_id)
        except (Institution.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not can_manage_curriculum(request.user, institution):
            return Response(
                {"detail": "Permission denied to manage curriculum for this institution."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {"status": "Curriculum management authorized for institution."},
            status=status.HTTP_200_OK,
        )
