"""
Deciding who hears about what.

Notifications are created here rather than at each call site so the rules
about who is interested in an event live in one place.
"""
import logging

from core.enums import MonographStage, NotificationKind

from notifications.models import Notification

logger = logging.getLogger(__name__)


def notify(recipient, kind, title, body="", monograph=None, actor=None, **metadata):
    """Create one notification and push it to the recipient's open screens."""
    if recipient is None or (actor is not None and recipient.id == actor.id):
        # Nobody needs telling about their own action.
        return None

    notification = Notification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        body=body,
        monograph=monograph,
        actor=actor,
        link=f"/monographs/{monograph.id}" if monograph else "",
        metadata=metadata,
    )

    from notifications.realtime import push_notification

    push_notification(notification)
    return notification


def notify_many(recipients, **kwargs):
    seen = set()
    created = []
    for recipient in recipients:
        if recipient is None or recipient.id in seen:
            continue
        seen.add(recipient.id)
        result = notify(recipient, **kwargs)
        if result:
            created.append(result)
    return created


def monograph_audience(monograph, include_students=True, include_staff=True):
    """
    Everyone with a stake in a monograph.

    Used as the default recipient list; individual events narrow it down.
    """
    people = []
    if include_students:
        people.extend(m.student for m in monograph.members.select_related("student"))
    if include_staff:
        if monograph.supervisor:
            people.append(monograph.supervisor)
        head = monograph.department.head
        if head:
            people.append(head)
    return people


#: Who should hear about each stage change, and how it should read.
#: Framed from the reader's point of view — a student is told what happened to
#: their work, not what the system did.
_STAGE_MESSAGES = {
    MonographStage.TOPIC_SUBMITTED: (
        "Topic submitted",
        "{title} has been submitted for approval.",
    ),
    MonographStage.TOPIC_APPROVED: (
        "Topic approved",
        "Your topic has been approved. You may now prepare your proposal.",
    ),
    MonographStage.PROPOSAL_SUBMITTED: (
        "Proposal submitted",
        "A proposal is waiting for your review.",
    ),
    MonographStage.UNDER_REVIEW: (
        "Your proposal is being reviewed",
        "Your supervisor has started reading your proposal.",
    ),
    MonographStage.REVISION_REQUIRED: (
        "Revision requested",
        "Your supervisor has asked for changes. Open the feedback to see what is needed.",
    ),
    MonographStage.PROPOSAL_APPROVED: (
        "Proposal approved",
        "Your proposal has been approved. You may begin your research.",
    ),
    MonographStage.RESEARCH_IN_PROGRESS: (
        "Research started",
        "Work on {title} is now in progress.",
    ),
    MonographStage.FINAL_SUBMISSION: (
        "Final monograph submitted",
        "A completed monograph is waiting for your final review.",
    ),
    MonographStage.FINAL_REVIEW: (
        "Final review started",
        "Your supervisor is reading your completed monograph.",
    ),
    MonographStage.DEFENSE_SCHEDULED: (
        "Defense scheduled",
        "A date has been set for the defense of {title}.",
    ),
    MonographStage.DEFENDED: (
        "Defense completed",
        "The defense of {title} has taken place.",
    ),
    MonographStage.COMPLETED: (
        "Monograph completed",
        "{title} is complete and has been added to the department archive.",
    ),
    MonographStage.REJECTED: (
        "Monograph rejected",
        "{title} has been rejected. See the recorded reason for details.",
    ),
    MonographStage.WITHDRAWN: (
        "Monograph withdrawn",
        "{title} has been withdrawn.",
    ),
}


def notify_monograph_stage_change(monograph, transition, rule, actor, kind):
    """Tell the right people that a monograph moved."""
    title, body_template = _STAGE_MESSAGES.get(
        transition.to_stage,
        ("Monograph updated", "{title} has moved to a new stage."),
    )
    body = body_template.format(title=monograph.title)
    if transition.note:
        body = f"{body}\n\n{transition.note}"

    # Work arriving for review concerns staff; a decision concerns the student.
    student_facing = transition.to_stage in {
        MonographStage.TOPIC_APPROVED,
        MonographStage.UNDER_REVIEW,
        MonographStage.REVISION_REQUIRED,
        MonographStage.PROPOSAL_APPROVED,
        MonographStage.FINAL_REVIEW,
        MonographStage.DEFENSE_SCHEDULED,
        MonographStage.DEFENDED,
        MonographStage.COMPLETED,
        MonographStage.REJECTED,
    }
    staff_facing = transition.to_stage in {
        MonographStage.TOPIC_SUBMITTED,
        MonographStage.PROPOSAL_SUBMITTED,
        MonographStage.FINAL_SUBMISSION,
        MonographStage.WITHDRAWN,
    }

    recipients = monograph_audience(
        monograph,
        include_students=student_facing,
        include_staff=staff_facing or student_facing,
    )

    notify_many(
        recipients,
        kind=kind,
        title=title,
        body=body,
        monograph=monograph,
        actor=actor,
        from_stage=transition.from_stage,
        to_stage=transition.to_stage,
    )


def notify_supervisor_assigned(monograph, supervisor, actor):
    notify_many(
        [m.student for m in monograph.members.select_related("student")],
        kind=NotificationKind.SUPERVISOR_ASSIGNED,
        title="Supervisor assigned",
        body=f"{supervisor.display_name} is now supervising your monograph.",
        monograph=monograph,
        actor=actor,
    )
    notify(
        supervisor,
        kind=NotificationKind.SUPERVISOR_ASSIGNED,
        title="New student assigned",
        body=f"You are now supervising {monograph.title}.",
        monograph=monograph,
        actor=actor,
    )


def notify_review_submitted(review, actor):
    monograph = review.monograph
    notify_many(
        [m.student for m in monograph.members.select_related("student")],
        kind=NotificationKind.REVIEW_RECEIVED,
        title="Feedback received",
        body=review.summary or "Your supervisor has left feedback on your work.",
        monograph=monograph,
        actor=actor,
        decision=review.decision,
    )


def notify_document_uploaded(version, actor):
    monograph = version.document.monograph
    recipients = []
    if monograph.supervisor:
        recipients.append(monograph.supervisor)
    notify_many(
        recipients,
        kind=NotificationKind.SUBMISSION_RECEIVED,
        title="New submission",
        body=f"{version.document.title} (version {version.version_number}) was uploaded.",
        monograph=monograph,
        actor=actor,
    )


def notify_deadline(monograph, deadline, missed=False):
    kind = (
        NotificationKind.DEADLINE_MISSED if missed else NotificationKind.DEADLINE_APPROACHING
    )
    title = "Deadline passed" if missed else "Deadline approaching"
    body = (
        f"The deadline for {deadline.stage.replace('_', ' ')} "
        f"{'passed on' if missed else 'is'} {deadline.due_date}."
    )
    notify_many(
        monograph_audience(monograph),
        kind=kind,
        title=title,
        body=body,
        monograph=monograph,
        stage=deadline.stage,
        due_date=str(deadline.due_date),
    )
