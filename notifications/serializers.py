from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "event_type",
            "subject",
            "preview",
            "payload",
            "delivery_status",
            "read_status",
            "read_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "event_type",
            "subject",
            "preview",
            "payload",
            "delivery_status",
            "read_status",
            "read_at",
            "created_at",
        ]


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkAllReadSerializer(serializers.Serializer):
    updated_count = serializers.IntegerField()
