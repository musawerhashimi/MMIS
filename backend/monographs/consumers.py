"""
Websocket consumer for a single monograph's live view.

Subscribing is an access decision, not a routing detail: a student must not
be able to watch another student's monograph simply by knowing its id, so
membership is checked before the connection is accepted.
"""
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from monographs.realtime import monograph_group

logger = logging.getLogger(__name__)


class MonographConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)  # unauthenticated
            return

        self.monograph_id = self.scope["url_route"]["kwargs"]["monograph_id"]

        if not await self._may_watch(user, self.monograph_id):
            await self.close(code=4403)  # not involved in this monograph
            return

        self.group = monograph_group(self.monograph_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"event": "connected", "monograph_id": str(self.monograph_id)})

    async def disconnect(self, code):
        group = getattr(self, "group", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # The client only ever needs to keep the connection alive.
        if content.get("action") == "ping":
            await self.send_json({"event": "pong"})

    async def monograph_event(self, message):
        await self.send_json(
            {
                "event": message["event"],
                "monograph_id": message["monograph_id"],
                "data": message["data"],
            }
        )

    @database_sync_to_async
    def _may_watch(self, user, monograph_id) -> bool:
        from monographs.models import Monograph

        try:
            monograph = Monograph.objects.get(pk=monograph_id)
        except (Monograph.DoesNotExist, ValueError):
            return False
        return monograph.is_visible_to(user)
