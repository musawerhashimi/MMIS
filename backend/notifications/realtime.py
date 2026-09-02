"""Delivering notifications to open browser tabs."""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def user_group(user_id) -> str:
    return f"user.{user_id}"


def push_notification(notification) -> None:
    """
    Send one notification to every screen the recipient has open.

    Best-effort: the notification is already saved, so a delivery failure only
    means the reader sees it on their next page load instead of instantly.
    """
    layer = get_channel_layer()
    if layer is None:
        return

    unread = notification.recipient.notifications.filter(read_at__isnull=True).count()

    try:
        async_to_sync(layer.group_send)(
            user_group(notification.recipient_id),
            {
                "type": "notification.message",
                "data": {
                    "id": str(notification.id),
                    "kind": notification.kind,
                    "title": notification.title,
                    "body": notification.body,
                    "link": notification.link,
                    "monograph_id": str(notification.monograph_id)
                    if notification.monograph_id
                    else None,
                    "actor": notification.actor.full_name if notification.actor else None,
                    "created_at": notification.created_at.isoformat(),
                },
                "unread_count": unread,
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("Could not push notification %s", notification.id)
