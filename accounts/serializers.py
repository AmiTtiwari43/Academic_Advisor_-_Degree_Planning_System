from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import AdvisorAssignment, InstitutionMembership, Role, UserProfile


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
    registration_number = serializers.CharField(max_length=64, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    username = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    institution_name = serializers.SerializerMethodField()
    academic_summary = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "registration_number",
            "phone_number",
            "preferred_name",
            "first_name",
            "last_name",
            "email",
            "username",
            "role",
            "institution_name",
            "academic_summary",
        ]

    def get_username(self, obj: UserProfile) -> str:
        return obj.user.username

    def get_role(self, obj: UserProfile) -> str:
        mem = obj.user.institution_memberships.filter(is_active=True).first()
        if not mem:
            return "Moderator" if obj.user.is_superuser else "Student"
        role = mem.role
        if role in [Role.ADMIN, Role.COORDINATOR, Role.HOD, Role.MODERATOR] or obj.user.is_superuser:
            return "Moderator"
        elif role in [Role.ADVISOR, Role.MENTOR, "FACULTY"]:
            return "Mentor"
        elif role == Role.STUDENT:
            return "Student"
        return role

    def get_institution_name(self, obj: UserProfile) -> str:
        mem = obj.user.institution_memberships.filter(is_active=True).select_related("institution").first()
        return mem.institution.name if mem and mem.institution else "Metropolitan State University"

    def get_academic_summary(self, obj: UserProfile) -> dict:
        summary = {}
        try:
            from academic_records.models import StudentRecord
            from accounts.models import AdvisorAssignment

            student_rec = (
                StudentRecord.objects.filter(student=obj.user)
                .select_related("programme", "enrollment_term")
                .first()
            )
            if student_rec:
                advisor_assign = (
                    AdvisorAssignment.objects.filter(student__user=obj.user, is_active=True)
                    .select_related("advisor__user")
                    .first()
                )
                adv_name = (
                    advisor_assign.advisor.user.get_full_name()
                    if advisor_assign and advisor_assign.advisor and advisor_assign.advisor.user
                    else "Not Assigned"
                )
                summary = {
                    "programme": student_rec.programme.name,
                    "programme_code": student_rec.programme.code,
                    "cgpa": f"{float(student_rec.cached_cgpa):.2f} / 10.00",
                    "credits_earned": float(student_rec.cached_total_credits),
                    "status": student_rec.status,
                    "enrollment_term": (
                        student_rec.enrollment_term.name if student_rec.enrollment_term else "Fall 2024"
                    ),
                    "advisor": adv_name,
                }
        except Exception:
            pass
        return summary

    def to_representation(self, instance: UserProfile) -> dict:
        ret = super().to_representation(instance)
        ret["first_name"] = instance.user.first_name
        ret["last_name"] = instance.user.last_name
        ret["email"] = instance.user.email
        return ret


class UserMeSerializer(serializers.ModelSerializer):
    preferred_name = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    registration_number = serializers.SerializerMethodField()
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
            "registration_number",
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

    def get_registration_number(self, obj: User) -> str:
        profile = getattr(obj, "profile", None)
        if profile:
            return profile.get_or_generate_registration_number()
        return f"REG-2026-{obj.id:04d}"

    def get_memberships(self, obj: User) -> list[dict]:
        memberships = InstitutionMembership.objects.filter(user=obj, is_active=True).select_related(
            "institution"
        )
        return list(InstitutionMembershipSummarySerializer(memberships, many=True).data)


class AdvisorAssignmentSerializer(serializers.ModelSerializer):
    advisor_name = serializers.CharField(source="advisor.user.get_full_name", read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    advisor_registration_number = serializers.SerializerMethodField()
    student_registration_number = serializers.SerializerMethodField()

    class Meta:
        model = AdvisorAssignment
        fields = [
            "id",
            "institution",
            "advisor",
            "student",
            "advisor_name",
            "student_name",
            "advisor_registration_number",
            "student_registration_number",
            "is_active",
            "assigned_at",
            "end_date",
        ]
        read_only_fields = ["id", "assigned_at"]

    def get_advisor_registration_number(self, obj: AdvisorAssignment) -> str:
        profile = getattr(obj.advisor.user, "profile", None)
        return profile.get_or_generate_registration_number() if profile else f"FAC-2026-{obj.advisor.user_id:04d}"

    def get_student_registration_number(self, obj: AdvisorAssignment) -> str:
        profile = getattr(obj.student.user, "profile", None)
        return profile.get_or_generate_registration_number() if profile else f"STU-2026-{obj.student.user_id:04d}"
