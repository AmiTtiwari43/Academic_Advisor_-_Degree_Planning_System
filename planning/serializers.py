from rest_framework import serializers

from planning.models import Plan, PlanItem, PlanVersion


class PlanItemSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_credits = serializers.DecimalField(
        source="course.credits", max_digits=5, decimal_places=2, read_only=True
    )
    term_code = serializers.CharField(source="planned_term.code", read_only=True)
    term_name = serializers.CharField(source="planned_term.name", read_only=True)

    class Meta:
        model = PlanItem
        fields = [
            "id",
            "institution",
            "plan",
            "course",
            "course_code",
            "course_title",
            "course_credits",
            "planned_term",
            "term_code",
            "term_name",
            "term_index",
            "position",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PlanSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(
        source="student_record.student.username", read_only=True
    )
    student_first_name = serializers.CharField(
        source="student_record.student.first_name", read_only=True
    )
    student_last_name = serializers.CharField(
        source="student_record.student.last_name", read_only=True
    )
    curriculum_version_number = serializers.IntegerField(
        source="curriculum_version.version_number", read_only=True
    )
    programme_code = serializers.CharField(
        source="curriculum_version.programme.code", read_only=True
    )
    programme_name = serializers.CharField(
        source="curriculum_version.programme.name", read_only=True
    )
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id",
            "institution",
            "student_record",
            "student_username",
            "student_first_name",
            "student_last_name",
            "curriculum_version",
            "curriculum_version_number",
            "programme_code",
            "programme_name",
            "name",
            "is_primary",
            "status",
            "row_version",
            "items_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "row_version", "created_at", "updated_at"]

    def get_items_count(self, obj: Plan) -> int:
        return obj.items.count()


class PlanDetailSerializer(PlanSerializer):
    items = PlanItemSerializer(many=True, read_only=True)

    class Meta(PlanSerializer.Meta):
        fields = PlanSerializer.Meta.fields + ["items"]


class PlanVersionSerializer(serializers.ModelSerializer):
    submitted_by_username = serializers.CharField(
        source="submitted_by.username", read_only=True
    )

    class Meta:
        model = PlanVersion
        fields = [
            "id",
            "institution",
            "plan",
            "version_number",
            "snapshot_data",
            "status",
            "submitted_by",
            "submitted_by_username",
            "submission_note",
            "submitted_at",
        ]
        read_only_fields = ["id", "submitted_at"]


class PlanUpdatePayloadSerializer(serializers.Serializer):
    expected_row_version = serializers.IntegerField(required=True)
    name = serializers.CharField(required=False, max_length=120)
    is_primary = serializers.BooleanField(required=False)


class AddCoursePayloadSerializer(serializers.Serializer):
    course_id = serializers.UUIDField(required=True)
    planned_term_id = serializers.UUIDField(required=True)
    term_index = serializers.IntegerField(required=True, min_value=1)
    position = serializers.IntegerField(required=False, min_value=0)
    expected_row_version = serializers.IntegerField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class MoveCoursePayloadSerializer(serializers.Serializer):
    plan_item_id = serializers.UUIDField(required=True)
    target_term_id = serializers.UUIDField(required=True)
    target_term_index = serializers.IntegerField(required=True, min_value=1)
    target_position = serializers.IntegerField(required=False, default=0, min_value=0)
    expected_row_version = serializers.IntegerField(required=False)


class RemoveCoursePayloadSerializer(serializers.Serializer):
    plan_item_id = serializers.UUIDField(required=True)
    expected_row_version = serializers.IntegerField(required=False)


class SubmitPlanPayloadSerializer(serializers.Serializer):
    submission_note = serializers.CharField(required=False, allow_blank=True, default="")


class WhatIfPayloadSerializer(serializers.Serializer):
    student_record_id = serializers.UUIDField(required=True)
    target_curriculum_version_id = serializers.UUIDField(required=True)
    plan_id = serializers.UUIDField(required=False, allow_null=True)


class ReviewActionPayloadSerializer(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True, default="")
    expected_row_version = serializers.IntegerField(required=False)
    idempotency_key = serializers.CharField(required=False, allow_null=True, max_length=128)
    version_number = serializers.IntegerField(required=False)


class OverridePayloadSerializer(serializers.Serializer):
    override_type = serializers.ChoiceField(
        choices=[
            ("PREREQUISITE_OVERRIDE", "Prerequisite Requirement Override"),
            ("CREDIT_CEILING_OVERRIDE", "Term Credit Ceiling Override"),
            ("OFFERING_OVERRIDE", "Course Offering Schedule Override"),
            ("GENERAL_OVERRIDE", "General Degree Requirement Override"),
        ]
    )
    justification = serializers.CharField(required=True, min_length=15)
    version_number = serializers.IntegerField(required=False)
    metadata = serializers.DictField(required=False, default=dict)


class PlanReviewDecisionSerializer(serializers.ModelSerializer):
    reviewer_username = serializers.CharField(source="reviewer.username", read_only=True)
    reviewer_first_name = serializers.CharField(source="reviewer.first_name", read_only=True)
    reviewer_last_name = serializers.CharField(source="reviewer.last_name", read_only=True)
    version_number = serializers.IntegerField(source="plan_version.version_number", read_only=True)

    class Meta:
        from planning.models import PlanReviewDecision
        model = PlanReviewDecision
        fields = [
            "id",
            "institution",
            "plan",
            "plan_version",
            "version_number",
            "reviewer",
            "reviewer_username",
            "reviewer_first_name",
            "reviewer_last_name",
            "action",
            "from_status",
            "to_status",
            "comments",
            "idempotency_key",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class OverrideEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)
    actor_first_name = serializers.CharField(source="actor.first_name", read_only=True)
    actor_last_name = serializers.CharField(source="actor.last_name", read_only=True)
    version_number = serializers.IntegerField(source="plan_version.version_number", read_only=True)

    class Meta:
        from planning.models import OverrideEvent
        model = OverrideEvent
        fields = [
            "id",
            "institution",
            "plan",
            "plan_version",
            "version_number",
            "actor",
            "actor_username",
            "actor_first_name",
            "actor_last_name",
            "override_type",
            "justification",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PlanAuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)
    actor_first_name = serializers.CharField(source="actor.first_name", read_only=True)
    actor_last_name = serializers.CharField(source="actor.last_name", read_only=True)
    version_number = serializers.IntegerField(
        source="plan_version.version_number", read_only=True, allow_null=True
    )

    class Meta:
        from planning.models import PlanAuditLog
        model = PlanAuditLog
        fields = [
            "id",
            "institution",
            "plan",
            "plan_version",
            "version_number",
            "actor",
            "actor_username",
            "actor_first_name",
            "actor_last_name",
            "action",
            "from_status",
            "to_status",
            "comment",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]



class ReviewQueueItemSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    plan_name = serializers.CharField()
    status = serializers.CharField()
    row_version = serializers.IntegerField()
    student_id = serializers.UUIDField()
    student_username = serializers.CharField()
    student_email = serializers.EmailField()
    programme_code = serializers.CharField()
    programme_name = serializers.CharField()
    latest_version_id = serializers.UUIDField(allow_null=True)
    latest_version_number = serializers.IntegerField()
    latest_version_status = serializers.CharField()
    submitted_at = serializers.CharField()
    waiting_days = serializers.IntegerField()
    override_count = serializers.IntegerField()
    hard_constraints_count = serializers.IntegerField()
    warnings_count = serializers.IntegerField()
    is_valid_for_submission = serializers.BooleanField()
    projected_graduation_term = serializers.CharField(allow_null=True)

