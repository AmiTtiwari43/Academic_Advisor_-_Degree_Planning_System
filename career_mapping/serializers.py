"""
Serializers for Career Objective and Skill Mapping APIs (Prompt 08D).
"""

from rest_framework import serializers

from career_mapping.models import (
    CareerObjective,
    CareerSkillRequirement,
    CourseSkillMapping,
    Skill,
    StudentCareerPreference,
)


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = [
            "id",
            "code",
            "name",
            "category",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value: str) -> str:
        return value.strip().upper()


class CareerSkillRequirementSerializer(serializers.ModelSerializer):
    skill_code = serializers.CharField(source="skill.code", read_only=True)
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    skill_category = serializers.CharField(source="skill.category", read_only=True)

    class Meta:
        model = CareerSkillRequirement
        fields = [
            "id",
            "career_objective",
            "skill",
            "skill_code",
            "skill_name",
            "skill_category",
            "min_proficiency",
            "is_critical",
            "display_order",
        ]
        read_only_fields = ["id"]


class CareerObjectiveSerializer(serializers.ModelSerializer):
    skill_requirements = CareerSkillRequirementSerializer(many=True, read_only=True)
    programme_code = serializers.CharField(source="programme.code", read_only=True)

    class Meta:
        model = CareerObjective
        fields = [
            "id",
            "code",
            "title",
            "description",
            "programme",
            "programme_code",
            "is_active",
            "skill_requirements",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value: str) -> str:
        return value.strip().upper()


class CourseSkillMappingSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    skill_code = serializers.CharField(source="skill.code", read_only=True)
    skill_name = serializers.CharField(source="skill.name", read_only=True)

    class Meta:
        model = CourseSkillMapping
        fields = [
            "id",
            "course",
            "course_code",
            "course_title",
            "skill",
            "skill_code",
            "skill_name",
            "proficiency_level",
            "coverage_weight",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StudentCareerPreferenceSerializer(serializers.ModelSerializer):
    career_objective_code = serializers.CharField(
        source="career_objective.code", read_only=True
    )
    career_objective_title = serializers.CharField(
        source="career_objective.title", read_only=True
    )
    target_term_code = serializers.CharField(
        source="target_term.code", read_only=True
    )

    class Meta:
        model = StudentCareerPreference
        fields = [
            "id",
            "student_record",
            "career_objective",
            "career_objective_code",
            "career_objective_title",
            "priority",
            "target_term",
            "target_term_code",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Analysis & Recommendation Read-Only Serializers
# ---------------------------------------------------------------------------


class AcquiredSkillInfoSerializer(serializers.Serializer):
    skill_id = serializers.CharField()
    skill_code = serializers.CharField()
    skill_name = serializers.CharField()
    skill_category = serializers.CharField()
    proficiency_level = serializers.CharField()
    proficiency_score = serializers.IntegerField()
    source_courses = serializers.ListField(child=serializers.CharField())


class TargetSkillRequirementSerializer(serializers.Serializer):
    skill_id = serializers.CharField()
    skill_code = serializers.CharField()
    skill_name = serializers.CharField()
    skill_category = serializers.CharField()
    min_proficiency = serializers.CharField()
    min_proficiency_score = serializers.IntegerField()
    is_critical = serializers.BooleanField()
    is_met = serializers.BooleanField()
    current_proficiency = serializers.CharField(allow_null=True)
    current_proficiency_score = serializers.IntegerField()
    status = serializers.CharField()


class SkillGapReportSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    student_username = serializers.CharField()
    career_objective_id = serializers.CharField()
    career_objective_code = serializers.CharField()
    career_objective_title = serializers.CharField()
    total_target_skills = serializers.IntegerField()
    total_critical_skills = serializers.IntegerField()
    critical_skills_met = serializers.IntegerField()
    recommended_skills_met = serializers.IntegerField()
    readiness_percentage = serializers.FloatField()
    satisfied_skills = TargetSkillRequirementSerializer(many=True)
    proficiency_gaps = TargetSkillRequirementSerializer(many=True)
    missing_skills = TargetSkillRequirementSerializer(many=True)
    acquired_skills = AcquiredSkillInfoSerializer(many=True)


class RecommendedSkillCoveredSerializer(serializers.Serializer):
    skill_id = serializers.CharField()
    skill_code = serializers.CharField()
    skill_name = serializers.CharField()
    proficiency_level = serializers.CharField()
    is_critical = serializers.BooleanField()


class CourseRecommendationSerializer(serializers.Serializer):
    course_id = serializers.CharField()
    course_code = serializers.CharField()
    course_title = serializers.CharField()
    credits = serializers.FloatField()
    relevance_score = serializers.FloatField()
    recommendation_type = serializers.CharField()
    satisfies_degree_requirement_group = serializers.CharField(allow_null=True)
    is_prerequisite_eligible = serializers.BooleanField()
    prerequisite_status_message = serializers.CharField()
    skills_covered = RecommendedSkillCoveredSerializer(many=True)
    explanation = serializers.CharField()
