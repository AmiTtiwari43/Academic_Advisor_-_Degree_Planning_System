from typing import Any

from rest_framework import serializers

from academic_records.models import (
    AcademicTerm,
    Exemption,
    StudentRecord,
    TranscriptEntry,
    TransferCredit,
)
from academic_records.services.context_builder import compute_semester_gpas
from rule_engine.core.context import DEFAULT_GRADE_SCALE


class AcademicTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicTerm
        fields = [
            "id",
            "institution",
            "code",
            "name",
            "season",
            "year",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TranscriptEntrySerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    term_code = serializers.CharField(source="term.code", read_only=True)
    grade_points = serializers.SerializerMethodField()

    def get_grade_points(self, obj) -> float | None:
        if not obj.grade:
            return None
        return DEFAULT_GRADE_SCALE.get(obj.grade.strip().upper())

    class Meta:
        model = TranscriptEntry
        fields = [
            "id",
            "institution",
            "student_record",
            "course",
            "course_code",
            "course_title",
            "term",
            "term_code",
            "grade",
            "grade_points",
            "credits_attempted",
            "credits_earned",
            "status",
            "verification_status",
            "attempt_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TransferCreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferCredit
        fields = [
            "id",
            "institution",
            "student_record",
            "course_code",
            "course_title",
            "source_institution",
            "credits",
            "grade",
            "is_verified",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ExemptionSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    approved_by_username = serializers.CharField(
        source="approved_by.username", read_only=True
    )

    class Meta:
        model = Exemption
        fields = [
            "id",
            "institution",
            "student_record",
            "course",
            "course_code",
            "course_title",
            "reason",
            "approved_by",
            "approved_by_username",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "approved_at", "created_at", "updated_at"]


class StudentRecordSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source="student.username", read_only=True)
    student_first_name = serializers.CharField(source="student.first_name", read_only=True)
    student_last_name = serializers.CharField(source="student.last_name", read_only=True)
    student_preferred_name = serializers.SerializerMethodField()
    student_registration_number = serializers.SerializerMethodField()
    student_email = serializers.CharField(source="student.email", read_only=True)
    programme_code = serializers.CharField(source="programme.code", read_only=True)
    programme_name = serializers.CharField(source="programme.name", read_only=True)
    curriculum_version_number = serializers.IntegerField(
        source="pinned_curriculum.version_number", read_only=True
    )
    enrollment_term_code = serializers.CharField(
        source="enrollment_term.code", read_only=True
    )

    def get_student_preferred_name(self, obj: StudentRecord) -> str:
        profile = getattr(obj.student, "profile", None)
        return profile.preferred_name if profile and profile.preferred_name else ""

    def get_student_registration_number(self, obj: StudentRecord) -> str:
        profile = getattr(obj.student, "profile", None)
        if profile:
            return profile.get_or_generate_registration_number()
        return f"STU-2026-{obj.student_id:04d}"

    class Meta:
        model = StudentRecord
        fields = [
            "id",
            "institution",
            "student",
            "student_username",
            "student_first_name",
            "student_last_name",
            "student_preferred_name",
            "student_registration_number",
            "student_email",
            "programme",
            "programme_code",
            "programme_name",
            "pinned_curriculum",
            "curriculum_version_number",
            "enrollment_term",
            "enrollment_term_code",
            "expected_graduation_term",
            "repeated_course_policy",
            "status",
            "cached_cgpa",
            "cached_total_credits",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "cached_cgpa",
            "cached_total_credits",
            "created_at",
            "updated_at",
        ]


class StudentRecordDetailSerializer(StudentRecordSerializer):
    transcript_entries = TranscriptEntrySerializer(many=True, read_only=True)
    transfer_credits = TransferCreditSerializer(many=True, read_only=True)
    exemptions = ExemptionSerializer(many=True, read_only=True)
    semester_summaries = serializers.SerializerMethodField()

    def get_semester_summaries(self, obj) -> list[dict[str, Any]]:
        return compute_semester_gpas(obj)

    class Meta(StudentRecordSerializer.Meta):
        fields = StudentRecordSerializer.Meta.fields + [
            "transcript_entries",
            "transfer_credits",
            "exemptions",
            "semester_summaries",
        ]
