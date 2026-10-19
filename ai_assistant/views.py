from typing import Optional

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from institutions.models import Institution

from .serializers import (
    AssistantCapabilitiesSerializer,
    AssistantQuerySerializer,
    AssistantResponseSerializer,
)
from .services import answer_curriculum_query


class AssistantRateThrottle(UserRateThrottle):
    scope = "assistant"


def _get_active_institution(request: Request, institution_id: Optional[str] = None) -> Institution:
    """Helper to resolve and validate the request institution context."""
    user = request.user
    if institution_id:
        return get_object_or_404(Institution, id=institution_id)

    header_inst = request.headers.get("X-Institution-ID")
    if header_inst:
        try:
            return get_object_or_404(Institution, id=header_inst)
        except (ValueError, ValidationError):
            pass

    membership = user.institution_memberships.filter(is_active=True).first()
    if membership:
        return membership.institution

    raise PermissionDenied("Active institutional context required.")


class AssistantQueryView(APIView):
    """
    Processes curriculum and degree planning inquiries strictly grounded
    in authorized institution catalog and official degree records.
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AssistantRateThrottle]
    serializer_class = AssistantQuerySerializer

    @extend_schema(
        summary="Query Curriculum Assistant",
        description=(
            "Queries the curriculum-grounded AI assistant. Pre-retrieval authorization "
            "strictly isolates records by tenant and role. All prerequisite calculations "
            "are grounded in the authoritative pure-Python rule engine."
        ),
        request=AssistantQuerySerializer,
        responses={200: AssistantResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        prompt = serializer.validated_data["prompt"]
        student_record_id = serializer.validated_data.get("student_record_id")

        institution = _get_active_institution(request)

        # Execute grounded query synthesis (pre-retrieval authorization enforced internally)
        result = answer_curriculum_query(
            user=request.user,
            institution=institution,
            prompt=prompt,
            student_record_id=student_record_id,
        )

        response_serializer = AssistantResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class AssistantCapabilitiesView(APIView):
    """
    Returns assistant capabilities, grounded sources, and advisory notices.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssistantCapabilitiesSerializer

    @extend_schema(
        summary="Get Assistant Capabilities",
        description="Returns list of query capabilities, grounding sources, and rate limits.",
        responses={200: AssistantCapabilitiesSerializer},
    )
    def get(self, request: Request) -> Response:
        capabilities = {
            "supported_query_types": [
                "Course prerequisite validation",
                "Degree progress and graduation credit summary",
                "Remaining mandatory course requirements",
                "Institution course catalog exploration",
            ],
            "disclaimer": (
                "AI responses are grounded strictly in your institution's published curriculum "
                "and official degree audit records. The assistant cannot make exceptions, approve "
                "degree plans, or modify academic records. Always verify academic plans with your official advisor."
            ),
            "grounding_sources": [
                "Published Curriculum Versions",
                "Official Student Academic Records",
                "Degree Audit Engine",
                "Prerequisite Rule Interpreter",
            ],
            "rate_limit": "20 requests per minute per user",
        }
        return Response(capabilities, status=status.HTTP_200_OK)
