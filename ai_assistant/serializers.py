from rest_framework import serializers


class CitationSerializer(serializers.Serializer):
    source_type = serializers.CharField()
    reference = serializers.CharField()
    details = serializers.CharField()


class AssistantQuerySerializer(serializers.Serializer):
    prompt = serializers.CharField(
        max_length=1000,
        required=True,
        help_text="Academic question or degree planning query.",
    )
    student_record_id = serializers.CharField(
        max_length=64,
        required=False,
        allow_null=True,
        default=None,
        help_text="Optional student record ID (authorized advisors/coordinators only).",
    )


class AssistantResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    citations = CitationSerializer(many=True)
    grounded_context_summary = serializers.CharField()
    disclaimer = serializers.CharField()


class AssistantCapabilitiesSerializer(serializers.Serializer):
    supported_query_types = serializers.ListField(child=serializers.CharField())
    disclaimer = serializers.CharField()
    grounding_sources = serializers.ListField(child=serializers.CharField())
    rate_limit = serializers.CharField()
