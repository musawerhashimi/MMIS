"""Notification endpoints — the bell in the top bar."""
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.pagination import SmallPagination
from notifications.models import Notification
from notifications.serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A person's own notifications.

    Read-only apart from marking them read: notifications are produced by
    things happening, never posted directly.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SmallPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["kind", "monograph"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "actor", "monograph"
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Just the number, for the badge — cheap enough to poll."""
        return Response({"unread_count": self.get_queryset().unread().count()})

    @action(detail=False, methods=["get"])
    def unread(self, request):
        queryset = self.get_queryset().unread()
        page = self.paginate_queryset(queryset)
        serializer = NotificationSerializer(
            page if page is not None else queryset, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        count = self.get_queryset().unread().update(read_at=timezone.now())
        return Response({"marked": count, "unread_count": 0})
