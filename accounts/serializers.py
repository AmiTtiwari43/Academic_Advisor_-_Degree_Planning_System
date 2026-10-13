from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import AdvisorAssignment, InstitutionMembership, UserProfile


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)


class InstitutionMembershipSummarySerializer(serializers.ModelSerializer):
    institution_id = serializers.UUIDField(source="institution.id", read_only=True)
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    institution_code = serializers.CharField(source="institution.code", read_only=True)

    class Meta:
        model = InstitutionMembership
        fields = [
            "id",
            "institution_id",
            "institution_name",
            "institution_code",
            "role",
            "is_active",
        ]
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    preferred_name = serializers.CharField(max_length=128, required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = ["phone_number", "preferred_name"]


class UserMeSerializer(serializers.ModelSerializer):
    preferred_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "phone_number",
            "memberships",
            "is_staff",
            "is_superuser",
        ]
        read_only_fields = fields

    def get_preferred_name(self, obj: User) -> str:
        profile = getattr(obj, "profile", None)
        return profile.preferred_name if profile else ""

    def get_phone_number(self, obj: User) -> str:
        profile = getattr(obj, "profile", None)
        return profile.phone_number if profile else ""

    def get_memberships(self, obj: User) -> list[dict]:
        memberships = InstitutionMembership.objects.filter(
            user=obj, is_active=True
        ).select_related("institution")
        return list(InstitutionMembershipSummarySerializer(memberships, many=True).data)


class AdvisorAssignmentSerializer(serializers.ModelSerializer):
    advisor_name = serializers.CharField(source="advisor.user.get_full_name", read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)

    class Meta:
        model = AdvisorAssignment
        fields = [
            "id",
            "institution",
            "advisor",
            "student",
            "advisor_name",
            "student_name",
            "is_active",
            "assigned_at",
            "end_date",
        ]
        read_only_fields = ["id", "assigned_at"]
