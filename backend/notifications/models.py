"""
In-app notifications.

Delivery is inside the system, not by email: many students do not check email
regularly, so the notification bell is the channel that actually reaches
them.
"""
from django.db import models
from django.utils import timezone

from core.enums import NotificationKind
from core.models import BaseModel


class NotificationQuerySet(models.QuerySet):
    def unread(self):
        return self.filter(read_at__isnull=True)

    def for_user(self, user):
        return self.filter(recipient=user)


class Notification(BaseModel):
    recipient = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=32, choices=NotificationKind.choices, db_index=True)

    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    #: Where the bell should take the reader when they click it.
    monograph = models.ForeignKey(
        "monographs.Monograph",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    link = models.CharField(max_length=500, blank=True)

    actor = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["recipient", "read_at", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} for {self.recipient.username}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])
