"""Notification serializers."""
from rest_framework import serializers

from core.serializers import UserBriefSerializer
from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    monograph_title = serializers.CharField(source="monograph.title", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "kind",
            "kind_label",
            "title",
            "body",
            "link",
            "monograph",
            "monograph_title",
            "actor",
            "is_read",
            "read_at",
            "metadata",
            "created_at",
        )
