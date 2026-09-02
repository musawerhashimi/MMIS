"""Live updates when a document is added or approved."""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _send(group: str, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(group, payload)
    except Exception:  # noqa: BLE001
        logger.exception("Could not broadcast to %s", group)


def broadcast_document_uploaded(monograph, version) -> None:
    from monographs.realtime import monograph_group

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
                "size": version.size_display,
                "uploaded_by": version.uploaded_by.full_name if version.uploaded_by else None,
                "at": version.created_at.isoformat(),
            },
        },
    )


def broadcast_document_approved(monograph, document, approver) -> None:
    from monographs.realtime import monograph_group

    _send(
        monograph_group(monograph.id),
        {
            "type": "monograph.event",
            "event": "document_approved",
            "monograph_id": str(monograph.id),
            "data": {
                "document_id": str(document.id),
                "title": document.title,
                "approved_by": approver.full_name if approver else None,
            },
        },
    )
