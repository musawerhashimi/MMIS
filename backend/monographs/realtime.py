"""
Pushing monograph changes to open screens.

Anyone viewing a monograph, and any head of department watching the
department dashboard, sees changes without reloading. Broadcasting is
deliberately best-effort: a dropped message must never roll back the change
it was describing.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def monograph_group(monograph_id) -> str:
    return f"monograph.{monograph_id}"


def department_group(department_id) -> str:
    return f"department.{department_id}"


def user_group(user_id) -> str:
    return f"user.{user_id}"


def _send(group: str, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(group, payload)
    except Exception:  # noqa: BLE001 - realtime is a convenience, never critical
        logger.exception("Could not broadcast to %s", group)


def broadcast_stage_change(monograph, transition) -> None:
    payload = {
        "type": "monograph.event",
        "event": "stage_changed",
        "monograph_id": str(monograph.id),
        "data": {
            "from_stage": transition.from_stage,
            "to_stage": transition.to_stage,
            "progress_percent": monograph.progress_percent,
            "actor": transition.actor.full_name if transition.actor else None,
            "note": transition.note,
            "at": transition.created_at.isoformat(),
        },
    }
    _send(monograph_group(monograph.id), payload)
    # The department dashboard counts by stage, so its numbers just changed.
    _send(department_group(monograph.department_id), {**payload, "type": "dashboard.event"})


def broadcast_activity(monograph, entry) -> None:
    _send(
        monograph_group(monograph.id),
        {
            "type": "monograph.event",
            "event": "activity",
            "monograph_id": str(monograph.id),
            "data": {
                "action": entry.action,
                "description": entry.description,
                "actor": entry.actor.full_name if entry.actor else None,
                "metadata": entry.metadata,
                "at": entry.created_at.isoformat(),
            },
        },
    )


def broadcast_document_uploaded(monograph, version) -> None:
    _send(
        monograph_group(monograph.id),
        {
            "type": "monograph.event",
            "event": "document_uploaded",
            "monograph_id": str(monograph.id),
            "data": {
                "document_id": str(version.document_id),
                "title": version.document.title,
                "document_type": version.document.document_type,
                "version": version.version_number,
                "uploaded_by": version.uploaded_by.full_name if version.uploaded_by else None,
                "at": version.created_at.isoformat(),
            },
        },
    )


def broadcast_review(monograph, review) -> None:
    _send(
        monograph_group(monograph.id),
        {
            "type": "monograph.event",
            "event": "review_submitted",
            "monograph_id": str(monograph.id),
            "data": {
                "review_id": str(review.id),
                "decision": review.decision,
                "reviewer": review.reviewer.full_name if review.reviewer else None,
                "at": review.created_at.isoformat(),
            },
        },
    )
