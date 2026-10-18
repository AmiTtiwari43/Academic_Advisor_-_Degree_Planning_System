from typing import Optional

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from institutions.models import Institution
from notifications.models import Notification, ReadStatus
from notifications.serializers import (
    MarkAllReadSerializer,
    NotificationSerializer,
    UnreadCountSerializer,
)
from notifications.services import (
    get_unread_notifications_count,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)


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


class NotificationListView(APIView):
    """
    Lists in-app notifications for the authenticated user scoped to the active institution.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    @extend_schema(
        summary="List Notifications",
        description="Returns list of in-app notifications for the requesting user.",
        parameters=[
            OpenApiParameter(
                "unread_only",
                type=bool,
                required=False,
                description="If true, returns only unread notifications.",
            ),
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        institution = _get_active_institution(request)
        user = request.user

        qs = Notification.objects.filter(recipient=user, institution=institution)
        unread_only = request.query_params.get("unread_only", "").lower() in ("true", "1")
        if unread_only:
            qs = qs.filter(read_status=ReadStatus.UNREAD)

        # Cap list to top 50 notifications
        notifications = qs[:50]
        serializer = self.serializer_class(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    """
    Marks a single notification as read.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer

    @extend_schema(
        summary="Mark Notification Read",
        description="Marks a specific notification owned by the user as read.",
        request=None,
        responses={200: NotificationSerializer},
    )
    def post(self, request: Request, pk: str) -> Response:
        try:
            notification = mark_notification_as_read(notification_id=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    """
    Marks all notifications for current user as read in the active institution.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MarkAllReadSerializer

    @extend_schema(
        summary="Mark All Notifications Read",
        description="Marks all unread notifications for the user as read in the active institution.",
        request=None,
        responses={200: MarkAllReadSerializer},
    )
    def post(self, request: Request) -> Response:
        institution = _get_active_institution(request)
        updated_count = mark_all_notifications_as_read(user=request.user, institution=institution)
        return Response({"updated_count": updated_count}, status=status.HTTP_200_OK)


class NotificationUnreadCountView(APIView):
    """
    Returns unread notifications count for the authenticated user.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UnreadCountSerializer

    @extend_schema(
        summary="Get Unread Count",
        description="Returns the total count of unread notifications.",
        responses={200: UnreadCountSerializer},
    )
    def get(self, request: Request) -> Response:
        institution = _get_active_institution(request)
        count = get_unread_notifications_count(user=request.user, institution=institution)
        return Response({"unread_count": count}, status=status.HTTP_200_OK)
