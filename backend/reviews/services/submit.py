"""
Recording a supervisor's decision.

A review is rarely just a comment: approving a proposal moves the monograph
forward, asking for revisions sends it back. Writing the review and moving the
stage happen together here so the two can never disagree.
"""
import logging

from django.db import transaction

from core.enums import MonographStage, ReviewDecision
from core.exceptions import DomainError
from monographs.services.transitions import log_activity, perform_transition
from reviews.models import Review, ReviewComment

logger = logging.getLogger(__name__)


#: Which stage a decision moves the monograph to, given where it is now.
#: A decision that has no entry for the current stage is recorded as feedback
#: without moving anything.
_STAGE_EFFECT = {
    MonographStage.PROPOSAL_SUBMITTED: {
        ReviewDecision.APPROVED: MonographStage.PROPOSAL_APPROVED,
        ReviewDecision.REVISION_REQUESTED: MonographStage.REVISION_REQUIRED,
        ReviewDecision.REJECTED: MonographStage.REJECTED,
    },
    MonographStage.UNDER_REVIEW: {
        ReviewDecision.APPROVED: MonographStage.PROPOSAL_APPROVED,
        ReviewDecision.REVISION_REQUESTED: MonographStage.REVISION_REQUIRED,
        ReviewDecision.REJECTED: MonographStage.REJECTED,
    },
    MonographStage.FINAL_SUBMISSION: {
        ReviewDecision.REVISION_REQUESTED: MonographStage.RESEARCH_IN_PROGRESS,
    },
    MonographStage.FINAL_REVIEW: {
        ReviewDecision.REVISION_REQUESTED: MonographStage.RESEARCH_IN_PROGRESS,
    },
}


@transaction.atomic
def submit_review(
    monograph,
    reviewer,
    decision: str,
    summary: str = "",
    comments: str = "",
    document_version=None,
    score=None,
    items: list[dict] | None = None,
    move_stage: bool = True,
):
    """
    Save a decision, its written feedback, and move the monograph if the
    decision calls for it.

    Returns (review, transition or None).
    """
    if not _may_review(monograph, reviewer):
        raise DomainError("Only this monograph's supervisor can review its work.")

    if decision == ReviewDecision.REVISION_REQUESTED and not (comments.strip() or items):
        raise DomainError(
            "Say what needs to change.",
            details={"comments": "Write the corrections the student must make."},
        )

    review = Review.objects.create(
        monograph=monograph,
        document_version=document_version,
        reviewer=reviewer,
        decision=decision,
        summary=summary,
        comments=comments,
        score=score,
        round_number=_next_round(monograph, document_version),
        created_by=reviewer,
    )

    for item in items or []:
        ReviewComment.objects.create(
            review=review,
            page_number=item.get("page_number"),
            section=item.get("section", ""),
            body=item["body"],
            created_by=reviewer,
        )

    log_activity(
        monograph,
        reviewer,
        action="review_submitted",
        description=f"Review recorded: {dict(ReviewDecision.choices)[decision]}.",
        review_id=str(review.id),
        decision=decision,
    )

    transition = None
    if move_stage:
        target = _STAGE_EFFECT.get(monograph.stage, {}).get(decision)
        if target:
            note = comments or summary or dict(ReviewDecision.choices)[decision]
            transition = perform_transition(
                monograph=monograph, user=reviewer, target=target, note=note
            )

    transaction.on_commit(lambda: _announce(review, reviewer))
    return review, transition


def _may_review(monograph, user) -> bool:
    if user.is_admin:
        return True
    if monograph.supervisor_id == user.id:
        return True
    if user.is_head_of_department:
        return monograph.department_id in user.headed_departments.values_list("id", flat=True)
    return False


def _next_round(monograph, document_version) -> int:
    """
    Which round of revision this is.

    Counted per document where one is given, so "chapter 3, round 2" reads
    correctly even while the proposal is on round 5.
    """
    queryset = monograph.reviews.all()
    if document_version is not None:
        queryset = queryset.filter(document_version__document=document_version.document)
    return queryset.count() + 1


def _announce(review, reviewer):
    from monographs.realtime import broadcast_review
    from notifications.services import notify_review_submitted

    try:
        notify_review_submitted(review, reviewer)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to notify about review %s", review.id)
    try:
        broadcast_review(review.monograph, review)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to broadcast review %s", review.id)
