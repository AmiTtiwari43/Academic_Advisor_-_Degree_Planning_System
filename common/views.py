from datetime import datetime, timezone

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    version = serializers.CharField()
    timestamp = serializers.CharField()


@extend_schema(
    summary="Service Health Check",
    description="Public health check endpoint for monitoring, load balancers, and container orchestration.",
    responses={200: HealthResponseSerializer},
    auth=[],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Public health check endpoint returning service liveness and timestamp.
    """
    return Response(
        {
            "status": "ok",
            "service": "academic-advisor-system",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
