from rest_framework import serializers

from institutions.models import Department, Institution


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "code",
            "domain",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            "id",
            "institution",
            "name",
            "code",
            "created_at",
        ]
        read_only_fields = fields
