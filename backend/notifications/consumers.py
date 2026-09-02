"""
The per-user websocket: notifications and unread counts.

Every signed-in tab holds one of these open, so it is kept deliberately
light — it sends the unread count on connect and then only pushes new
notifications as they arrive.
"""
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .realtime import user_group

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user = user
        self.group = user_group(user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        await self.send_json(
            {"event": "connected", "unread_count": await self._unread_count()}
        )

    async def disconnect(self, code):
        group = getattr(self, "group", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        if action == "ping":
            await self.send_json({"event": "pong"})
        elif action == "mark_read":
            await self._mark_read(content.get("id"))
            await self.send_json(
                {"event": "unread_count", "unread_count": await self._unread_count()}
            )
        elif action == "mark_all_read":
            await self._mark_all_read()
            await self.send_json({"event": "unread_count", "unread_count": 0})

    async def notification_message(self, message):
        await self.send_json(
            {
                "event": "notification",
                "data": message["data"],
                "unread_count": message.get("unread_count"),
            }
        )

    @database_sync_to_async
    def _unread_count(self) -> int:
        return self.user.notifications.filter(read_at__isnull=True).count()

    @database_sync_to_async
    def _mark_read(self, notification_id):
        from django.utils import timezone

        if not notification_id:
            return
        self.user.notifications.filter(id=notification_id, read_at__isnull=True).update(
            read_at=timezone.now()
        )

    @database_sync_to_async
    def _mark_all_read(self):
        from django.utils import timezone

        self.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
