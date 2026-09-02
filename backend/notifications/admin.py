"""In-app notifications."""
from django.contrib import admin

from core.admin import BaseModelAdmin
from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(BaseModelAdmin):
    """
    Produced by things happening rather than written by hand, so this is
    for looking at what was sent, not for sending anything.
    """

    list_display = ("created_at", "recipient", "kind", "title", "is_read")
    list_filter = ("kind", "read_at", "created_at")
    search_fields = ("recipient__full_name", "title", "body")
    date_hierarchy = "created_at"

    @admin.display(boolean=True, description="Read")
    def is_read(self, obj):
        return obj.is_read

    def has_add_permission(self, request):
        return False
