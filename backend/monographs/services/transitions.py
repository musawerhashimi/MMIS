"""
Executing a stage change.

Every stage move in the system goes through ``perform_transition``. Nothing
writes ``monograph.stage`` directly. That is what makes the history complete:
if the only door is here, no move can happen without a record of it.
"""
import logging

from django.db import transaction
from django.utils import timezone

from core.enums import MonographStage, NotificationKind
from core.exceptions import InvalidStageTransition, WorkflowPermissionDenied
from monographs import workflow
from monographs.models import ActivityLog, Monograph, StageTransition

logger = logging.getLogger(__name__)


@transaction.atomic
def perform_transition(
    monograph: Monograph,
    user,
    target: str,
    note: str = "",
    metadata: dict | None = None,
) -> StageTransition:
    """
    Move a monograph to a new stage, or raise explaining why it cannot.

    The row is locked for the duration so two people clicking at the same
    moment cannot both move it — the second request re-reads the new stage and
    fails cleanly instead of silently overwriting.

    Because the row is re-read here, the caller's own object is stale once
    this returns. Call ``refresh_from_db()`` before using it again, and never
    ``save()`` a whole stale instance afterwards — it would write the old
    stage straight back over the new one.
    """
    monograph = Monograph.objects.select_for_update().get(pk=monograph.pk)

    rule = workflow.get_transition(monograph.stage, target)
    allowed, reason, denial = workflow.check_transition(monograph, user, target)
    if not allowed:
        # "You may not" is a 403; "that is not possible right now" is a 400.
        if denial == workflow.DENIED_ROLE:
            raise WorkflowPermissionDenied(reason)
        raise InvalidStageTransition(reason)

    if rule.requires_note and not note.strip():
        raise InvalidStageTransition(
            "A written explanation is required for this action.",
            details={"note": "This field is required."},
        )

    previous_stage = monograph.stage
    days_in_previous = (timezone.now() - monograph.stage_changed_at).days

    monograph.stage = target
    monograph.stage_changed_at = timezone.now()
    monograph.updated_by = user

    fields = ["stage", "stage_changed_at", "updated_by", "updated_at"]

    # Terminal stages must always carry the reason they ended.
    if target in (MonographStage.REJECTED, MonographStage.WITHDRAWN):
        monograph.closure_reason = note
        fields.append("closure_reason")

    if target == MonographStage.COMPLETED:
        monograph.completed_at = timezone.now()
        fields.append("completed_at")

    monograph.save(update_fields=fields)

    record = StageTransition.objects.create(
        monograph=monograph,
        from_stage=previous_stage,
        to_stage=target,
        actor=user,
        note=note,
        days_in_previous_stage=days_in_previous,
        created_by=user,
    )

    ActivityLog.objects.create(
        monograph=monograph,
        actor=user,
        action="stage_changed",
        description=rule.label or f"Moved to {target}",
        metadata={
            "from": previous_stage,
            "to": target,
            "days_in_previous_stage": days_in_previous,
            **(metadata or {}),
        },
        created_by=user,
    )

    # Everything below runs only once the transaction commits, so a failed
    # save never sends a notification about something that did not happen.
    transaction.on_commit(
        lambda: _announce(monograph, record, rule, user)
    )

    logger.info(
        "Monograph %s moved %s -> %s by %s",
        monograph.id, previous_stage, target, user.username,
    )
    return record


def _announce(monograph, record, rule, actor):
    """Tell the people involved, and refresh anyone watching a live screen."""
    from notifications.services import notify_monograph_stage_change
    from monographs.realtime import broadcast_stage_change

    try:
        notify_monograph_stage_change(
            monograph=monograph,
            transition=record,
            rule=rule,
            actor=actor,
            kind=NotificationKind.STAGE_CHANGED,
        )
    except Exception:  # noqa: BLE001 - a failed notice must not undo the move
        logger.exception("Failed to send notifications for transition %s", record.id)

    try:
        broadcast_stage_change(monograph, record)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to broadcast transition %s", record.id)


def log_activity(monograph, user, action: str, description: str, **metadata) -> ActivityLog:
    """
    Record something that happened which is not a stage move.

    Used for uploads, supervisor assignment, defense scheduling and comments,
    so one timeline tells the whole story.
    """
    entry = ActivityLog.objects.create(
        monograph=monograph,
        actor=user,
        action=action,
        description=description,
        metadata=metadata,
        created_by=user,
    )

    from monographs.realtime import broadcast_activity

    transaction.on_commit(lambda: broadcast_activity(monograph, entry))
    return entry
