from rest_framework import serializers

from curriculum.models import (
    Course,
    CourseOffering,
    CreditCategory,
    CurriculumVersion,
    PrerequisiteRule,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    StudentCurriculumAssignment,
)
from rule_engine.core import RuleValidationError, validate_rule_strict


class CreditCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditCategory
        fields = ["id", "code", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class CourseSerializer(serializers.ModelSerializer):
    default_credit_category_code = serializers.CharField(
        source="default_credit_category.code", read_only=True
    )

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "title",
            "description",
            "credits",
            "default_credit_category",
            "default_credit_category_code",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_code(self, value: str) -> str:
        return value.strip().upper()


class RequirementGroupCourseSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_credits = serializers.DecimalField(
        source="course.credits", max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = RequirementGroupCourse
        fields = [
            "id",
            "requirement_group",
            "course",
            "course_code",
            "course_title",
            "course_credits",
            "is_mandatory",
            "display_order",
        ]
        read_only_fields = ["id"]


class RequirementGroupSerializer(serializers.ModelSerializer):
    group_courses = RequirementGroupCourseSerializer(many=True, read_only=True)
    credit_category_code = serializers.CharField(source="credit_category.code", read_only=True)

    class Meta:
        model = RequirementGroup
        fields = [
            "id",
            "curriculum_version",
            "parent",
            "name",
            "group_type",
            "min_credits",
            "min_courses",
            "min_cgpa",
            "credit_category",
            "credit_category_code",
            "display_order",
            "group_courses",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PrerequisiteRuleSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = PrerequisiteRule
        fields = [
            "id",
            "curriculum_version",
            "course",
            "course_code",
            "course_title",
            "rule_json",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_rule_json(self, value: dict) -> dict:
        try:
            validate_rule_strict(value)
        except (RuleValidationError, ValueError) as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value


class CourseOfferingSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = CourseOffering
        fields = [
            "id",
            "course",
            "course_code",
            "course_title",
            "academic_term",
            "academic_year",
            "is_offered",
            "capacity",
            "delivery_mode",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CurriculumVersionSummarySerializer(serializers.ModelSerializer):
    published_by_username = serializers.CharField(source="published_by.username", read_only=True)

    class Meta:
        model = CurriculumVersion
        fields = [
            "id",
            "version_number",
            "academic_year",
            "status",
            "total_credits_required",
            "min_cgpa_required",
            "published_at",
            "published_by_username",
            "change_summary",
            "is_editable",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CurriculumVersionSerializer(serializers.ModelSerializer):
    programme_code = serializers.CharField(source="programme.code", read_only=True)
    programme_name = serializers.CharField(source="programme.name", read_only=True)
    published_by_username = serializers.CharField(source="published_by.username", read_only=True)
    requirement_groups = RequirementGroupSerializer(many=True, read_only=True)
    prerequisite_rules = PrerequisiteRuleSerializer(many=True, read_only=True)

    class Meta:
        model = CurriculumVersion
        fields = [
            "id",
            "programme",
            "programme_code",
            "programme_name",
            "version_number",
            "academic_year",
            "status",
            "total_credits_required",
            "min_cgpa_required",
            "published_at",
            "published_by",
            "published_by_username",
            "change_summary",
            "is_editable",
            "requirement_groups",
            "prerequisite_rules",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "published_at", "published_by"]


class ProgrammeSerializer(serializers.ModelSerializer):
    curriculum_versions = CurriculumVersionSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Programme
        fields = [
            "id",
            "code",
            "name",
            "degree_type",
            "department",
            "description",
            "is_active",
            "curriculum_versions",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_code(self, value: str) -> str:
        return value.strip().upper()


class StudentCurriculumAssignmentSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source="student.username", read_only=True)
    programme_code = serializers.CharField(
        source="curriculum_version.programme.code", read_only=True
    )
    programme_name = serializers.CharField(
        source="curriculum_version.programme.name", read_only=True
    )
    version_number = serializers.IntegerField(
        source="curriculum_version.version_number", read_only=True
    )
    academic_year = serializers.CharField(source="curriculum_version.academic_year", read_only=True)

    class Meta:
        model = StudentCurriculumAssignment
        fields = [
            "id",
            "student",
            "student_username",
            "curriculum_version",
            "programme_code",
            "programme_name",
            "version_number",
            "academic_year",
            "assigned_by",
            "assigned_at",
            "is_active",
        ]
        read_only_fields = ["id", "assigned_at"]


class GraphNodeSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    credits = serializers.FloatField()
    is_offered = serializers.BooleanField()
    metadata = serializers.DictField(required=False)


class GraphEdgeSerializer(serializers.Serializer):
    dependent = serializers.CharField()
    prerequisite = serializers.CharField()
    dependency_type = serializers.CharField()
    min_grade = serializers.CharField(allow_null=True)
    group_type = serializers.CharField()
    group_id = serializers.CharField(allow_null=True)


class CurriculumGraphResponseSerializer(serializers.Serializer):
    node_count = serializers.IntegerField()
    edge_count = serializers.IntegerField()
    has_cycle = serializers.BooleanField()
    cycles = serializers.ListField(child=serializers.ListField(child=serializers.CharField()))
    missing_references = serializers.ListField(child=serializers.CharField())
    nodes = GraphNodeSerializer(many=True)
    edges = GraphEdgeSerializer(many=True)


class DependencyChainStepSerializer(serializers.Serializer):
    course_code = serializers.CharField()
    course_title = serializers.CharField()
    dependency_type = serializers.CharField()
    min_grade = serializers.CharField(allow_null=True)
    depth = serializers.IntegerField()


class ExplainablePathSerializer(serializers.Serializer):
    target_course = serializers.CharField()
    root_prerequisite = serializers.CharField()
    path = serializers.ListField(child=serializers.CharField())
    steps = DependencyChainStepSerializer(many=True)
    explanation = serializers.CharField()


class GraphVisualizationSerializer(serializers.Serializer):
    svg = serializers.CharField()
    accessible_text = serializers.CharField()


class BlockedReasonSerializer(serializers.Serializer):
    course_code = serializers.CharField()
    missing_prerequisite = serializers.CharField()
    dependency_type = serializers.CharField()
    required_min_grade = serializers.CharField(allow_null=True)
    student_status = serializers.CharField(allow_null=True)
    student_grade = serializers.CharField(allow_null=True)
    is_direct = serializers.BooleanField()
    blocking_chain = serializers.ListField(child=serializers.CharField())
    message = serializers.CharField()


class BlockedByResponseSerializer(serializers.Serializer):
    course_code = serializers.CharField()
    is_blocked = serializers.BooleanField()
    direct_blockers = BlockedReasonSerializer(many=True)
    indirect_blockers = BlockedReasonSerializer(many=True)
    all_blocking_courses = serializers.ListField(child=serializers.CharField())
    unlocked_courses = serializers.ListField(child=serializers.CharField())
