"""
Background jobs that watch for things nobody is watching.

The point of this system is that a student cannot go quiet for two months
without anyone noticing. These tasks run nightly and raise the alarm while
there is still time to act, rather than at the end of the year when it is too
late to fix anything.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def check_approaching_deadlines(days_ahead: int = 7) -> dict:
    """
    Warn about deadlines that are close but not yet missed.

    Only warns once per deadline per monograph — a daily reminder for three
    weeks trains people to ignore the bell.
    """
    from core.enums import FINISHED_STAGES, NotificationKind, STAGE_ORDER, stage_index
    from monographs.models import Monograph
    from notifications.models import Notification
    from notifications.services import notify_deadline
    from organization.models import StageDeadline

    today = timezone.now().date()
    horizon = today + timedelta(days=days_ahead)

    upcoming = StageDeadline.objects.filter(
        due_date__gte=today, due_date__lte=horizon
    ).select_related("department", "academic_year")

    warned = 0
    for deadline in upcoming:
        target_index = stage_index(deadline.stage)
        if target_index <= 0:
            continue

        behind = (
            Monograph.objects.filter(
                department=deadline.department,
                academic_year=deadline.academic_year,
                stage__in=[str(s) for s in STAGE_ORDER[:target_index]],
            )
            .exclude(stage__in=FINISHED_STAGES)
            .prefetch_related("members__student")
        )

        for monograph in behind:
            already = Notification.objects.filter(
                monograph=monograph,
                kind=NotificationKind.DEADLINE_APPROACHING,
                metadata__stage=deadline.stage,
            ).exists()
            if already:
                continue
            notify_deadline(monograph, deadline, missed=False)
            warned += 1

    logger.info("Deadline warnings sent: %s", warned)
    return {"warned": warned}


@shared_task
def check_missed_deadlines() -> dict:
    """Tell people about deadlines that have already passed."""
    from core.enums import FINISHED_STAGES, NotificationKind, STAGE_ORDER, stage_index
    from monographs.models import Monograph
    from notifications.models import Notification
    from notifications.services import notify_deadline
    from organization.models import StageDeadline

    today = timezone.now().date()
    overdue = StageDeadline.objects.filter(due_date__lt=today).select_related(
        "department", "academic_year"
    )

    flagged = 0
    for deadline in overdue:
        target_index = stage_index(deadline.stage)
        if target_index <= 0:
            continue

        behind = (
            Monograph.objects.filter(
                department=deadline.department,
                academic_year=deadline.academic_year,
                stage__in=[str(s) for s in STAGE_ORDER[:target_index]],
            )
            .exclude(stage__in=FINISHED_STAGES)
            .prefetch_related("members__student")
        )

        for monograph in behind:
            already = Notification.objects.filter(
                monograph=monograph,
                kind=NotificationKind.DEADLINE_MISSED,
                metadata__stage=deadline.stage,
            ).exists()
            if already:
                continue
            notify_deadline(monograph, deadline, missed=True)
            flagged += 1

    logger.info("Missed deadline notices sent: %s", flagged)
    return {"flagged": flagged}


@shared_task
def flag_stalled_supervisors() -> dict:
    """
    Nudge supervisors sitting on work.

    Uses each department's own agreed response time rather than a fixed
    number, because departments differ on what counts as slow.
    """
    from core.enums import MonographStage, NotificationKind
    from monographs.models import Monograph
    from notifications.services import notify
    from organization.models import DepartmentPolicy

    awaiting_stages = [
        MonographStage.PROPOSAL_SUBMITTED,
        MonographStage.UNDER_REVIEW,
        MonographStage.FINAL_SUBMISSION,
        MonographStage.FINAL_REVIEW,
    ]

    nudged = 0
    for policy in DepartmentPolicy.objects.select_related("department"):
        cutoff = timezone.now() - timedelta(days=policy.supervisor_response_days)
        stalled = (
            Monograph.objects.filter(
                department=policy.department,
                stage__in=awaiting_stages,
                stage_changed_at__lt=cutoff,
                supervisor__isnull=False,
            )
            .select_related("supervisor")
        )

        for monograph in stalled:
            waiting = (timezone.now() - monograph.stage_changed_at).days
            notify(
                monograph.supervisor,
                kind=NotificationKind.DEADLINE_APPROACHING,
                title="A submission is still waiting",
                body=(
                    f"{monograph.title} has been waiting {waiting} days for your "
                    f"response."
                ),
                monograph=monograph,
                waiting_days=waiting,
            )
            # The head of department should see it too, since an overloaded
            # supervisor is their problem to solve.
            if policy.department.head:
                notify(
                    policy.department.head,
                    kind=NotificationKind.DEADLINE_APPROACHING,
                    title="Submission awaiting review",
                    body=(
                        f"{monograph.title} has waited {waiting} days for "
                        f"{monograph.supervisor.display_name}."
                    ),
                    monograph=monograph,
                    waiting_days=waiting,
                )
            nudged += 1

    logger.info("Stalled reviews flagged: %s", nudged)
    return {"nudged": nudged}


@shared_task
def flag_quiet_students() -> dict:
    """
    Notice students who have stopped working.

    This is the case the whole system exists to catch: a student going silent
    for months while nobody realises.
    """
    from core.enums import FINISHED_STAGES, NotificationKind
    from monographs.models import Monograph
    from notifications.services import notify, notify_many
    from organization.models import DepartmentPolicy

    flagged = 0
    for policy in DepartmentPolicy.objects.select_related("department"):
        cutoff = timezone.now() - timedelta(days=policy.student_inactivity_days)
        quiet = (
            Monograph.objects.filter(
                department=policy.department, stage_changed_at__lt=cutoff
            )
            .exclude(stage__in=FINISHED_STAGES)
            .select_related("supervisor")
            .prefetch_related("members__student")
        )

        for monograph in quiet:
            silent = (timezone.now() - monograph.stage_changed_at).days
            notify_many(
                [m.student for m in monograph.members.all()],
                kind=NotificationKind.DEADLINE_APPROACHING,
                title="Your monograph has not moved",
                body=(
                    f"There has been no progress on {monograph.title} for "
                    f"{silent} days. Contact your supervisor if you are stuck."
                ),
                monograph=monograph,
                silent_days=silent,
            )
            if monograph.supervisor:
                notify(
                    monograph.supervisor,
                    kind=NotificationKind.DEADLINE_APPROACHING,
                    title="A student has gone quiet",
                    body=f"{monograph.title} has not moved in {silent} days.",
                    monograph=monograph,
                    silent_days=silent,
                )
            flagged += 1

    logger.info("Quiet students flagged: %s", flagged)
    return {"flagged": flagged}


@shared_task
def remind_upcoming_defenses(days_ahead: int = 3) -> dict:
    """Remind committee members shortly before a defense."""
    from core.enums import NotificationKind
    from defenses.models import Defense
    from notifications.services import notify

    now = timezone.now()
    window_end = now + timedelta(days=days_ahead)

    upcoming = (
        Defense.objects.filter(scheduled_at__gte=now, scheduled_at__lte=window_end, result="")
        .select_related("monograph")
        .prefetch_related("committee__member")
    )

    reminded = 0
    for defense in upcoming:
        when = defense.scheduled_at.strftime("%Y-%m-%d at %H:%M")
        for seat in defense.committee.all():
            unread = "" if seat.has_read_monograph else " You have not marked it as read yet."
            notify(
                seat.member,
                kind=NotificationKind.DEFENSE_SCHEDULED,
                title="Defense coming up",
                body=f"{defense.monograph.title} — {when}, {defense.location}.{unread}",
                monograph=defense.monograph,
            )
            reminded += 1

    logger.info("Defense reminders sent: %s", reminded)
    return {"reminded": reminded}


@shared_task
def nightly_checks() -> dict:
    """
    Everything that should run once a day.

    Grouped into one task so the schedule has a single entry and the whole
    sweep either runs or visibly does not.
    """
    return {
        "approaching": check_approaching_deadlines(),
        "missed": check_missed_deadlines(),
        "stalled": flag_stalled_supervisors(),
        "quiet": flag_quiet_students(),
        "defenses": remind_upcoming_defenses(),
    }
