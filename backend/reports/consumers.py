"""
Live department dashboard.

The head of department watches counts that change as students and supervisors
act. Rather than pushing whole recalculated dashboards, this consumer tells
the client that something changed and lets it refetch — which keeps the
websocket light on a slow connection.
"""
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


def department_group(department_id) -> str:
    return f"department.{department_id}"


class DashboardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        # Only people who see department-wide figures may subscribe.
        if not (user.is_admin or user.is_head_of_department or user.can_supervise):
            await self.close(code=4403)
            return

        self.user = user
        self.groups_joined = [
            department_group(dept_id) for dept_id in await self._department_ids(user)
        ]
        for group in self.groups_joined:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()
        await self.send_json({"event": "connected", "departments": self.groups_joined})

    async def disconnect(self, code):
        for group in getattr(self, "groups_joined", []):
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("action") == "ping":
            await self.send_json({"event": "pong"})

    async def dashboard_event(self, message):
        """A monograph in a watched department changed."""
        await self.send_json(
            {
                "event": "dashboard_changed",
                "reason": message.get("event"),
                "monograph_id": message.get("monograph_id"),
                "data": message.get("data", {}),
            }
        )

    @database_sync_to_async
    def _department_ids(self, user) -> list[str]:
        if user.is_admin:
            from organization.models import Department

            return [str(pk) for pk in Department.objects.values_list("id", flat=True)]
        if user.is_head_of_department:
            return [str(pk) for pk in user.headed_departments.values_list("id", flat=True)]
        return [str(user.department_id)] if user.department_id else []
