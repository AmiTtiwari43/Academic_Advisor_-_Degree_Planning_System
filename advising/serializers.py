from rest_framework import serializers

from advising.models import (
    OverallRiskLevel,
    RiskAcknowledgment,
    RiskCategory,
    RiskSeverity,
    StudentRiskProfile,
)


class SourceRecordReferenceSerializer(serializers.Serializer):
    entity_type = serializers.CharField()
    record_id = serializers.CharField()
    display_name = serializers.CharField()


class RiskIndicatorSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    severity = serializers.ChoiceField(choices=RiskSeverity.choices)
    category = serializers.ChoiceField(choices=RiskCategory.choices)
    message = serializers.CharField()
    contributing_factors = serializers.DictField()
    source_records = SourceRecordReferenceSerializer(many=True)
    actionable_recommendation = serializers.CharField()


class RiskEvaluationResultSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    student_username = serializers.CharField()
    institution_id = serializers.CharField()
    overall_risk_level = serializers.ChoiceField(choices=OverallRiskLevel.choices)
    active_risk_count = serializers.IntegerField()
    critical_risk_count = serializers.IntegerField()
    warning_risk_count = serializers.IntegerField()
    info_risk_count = serializers.IntegerField()
    indicators = RiskIndicatorSerializer(many=True)
    assessed_at = serializers.CharField()
    summary = serializers.CharField()


class StudentRiskProfileModelSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source="student_record.student.username", read_only=True)
    programme_code = serializers.CharField(source="student_record.programme.code", read_only=True)
    programme_name = serializers.CharField(source="student_record.programme.name", read_only=True)

    class Meta:
        model = StudentRiskProfile
        fields = [
            "id",
            "institution",
            "student_record",
            "student_username",
            "programme_code",
            "programme_name",
            "overall_risk_level",
            "active_risk_count",
            "critical_risk_count",
            "warning_risk_count",
            "info_risk_count",
            "indicators",
            "summary",
            "assessed_at",
            "last_assessed_by",
        ]
        read_only_fields = [
            "id",
            "institution",
            "assessed_at",
            "active_risk_count",
            "critical_risk_count",
            "warning_risk_count",
            "info_risk_count",
            "indicators",
            "summary",
        ]


class RiskAcknowledgmentSerializer(serializers.ModelSerializer):
    advisor_username = serializers.CharField(source="advisor.username", read_only=True)

    class Meta:
        model = RiskAcknowledgment
        fields = [
            "id",
            "risk_profile",
            "indicator_code",
            "advisor",
            "advisor_username",
            "status",
            "notes",
            "action_plan",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "advisor", "created_at", "updated_at"]


class InstitutionRiskSummarySerializer(serializers.Serializer):
    institution_id = serializers.CharField()
    institution_name = serializers.CharField()
    programme_code = serializers.CharField(allow_null=True)
    total_assessed_students = serializers.IntegerField()
    risk_level_counts = serializers.DictField(child=serializers.IntegerField())
    critical_percentage = serializers.FloatField()
    action_required_count = serializers.IntegerField()
