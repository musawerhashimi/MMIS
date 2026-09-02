"""Supervisor decisions, and how they move the monograph."""
import pytest
from rest_framework import status

from core.enums import DocumentType, MonographStage as S, ReviewDecision
from core.exceptions import DomainError
from documents.models import Document
from reviews.services.submit import submit_review


@pytest.fixture
def under_review(supervised):
    Document.objects.create(
        monograph=supervised, document_type=DocumentType.PROPOSAL, title="Proposal"
    )
    supervised.stage = S.UNDER_REVIEW
    supervised.save()
    return supervised


@pytest.mark.django_db
class TestDecisionsMoveTheMonograph:
    def test_approving_a_proposal_lets_the_research_begin(
        self, under_review, supervisor
    ):
        _review, transition = submit_review(
            under_review, supervisor, ReviewDecision.APPROVED, summary="Good."
        )
        under_review.refresh_from_db()
        assert transition.to_stage == S.PROPOSAL_APPROVED
        assert under_review.stage == S.PROPOSAL_APPROVED

    def test_requesting_revisions_sends_it_back(self, under_review, supervisor):
        _review, transition = submit_review(
            under_review, supervisor, ReviewDecision.REVISION_REQUESTED,
            comments="The objectives are too broad.",
        )
        under_review.refresh_from_db()
        assert transition.to_stage == S.REVISION_REQUIRED
        assert under_review.stage == S.REVISION_REQUIRED

    def test_feedback_can_be_left_without_moving_anything(
        self, under_review, supervisor
    ):
        _review, transition = submit_review(
            under_review, supervisor, ReviewDecision.APPROVED,
            summary="Looks fine so far.", move_stage=False,
        )
        under_review.refresh_from_db()
        assert transition is None
        assert under_review.stage == S.UNDER_REVIEW


@pytest.mark.django_db
class TestWritingAReview:
    def test_revisions_must_say_what_to_change(self, under_review, supervisor):
        """A student cannot act on 'revise this' with no detail."""
        with pytest.raises(DomainError):
            submit_review(
                under_review, supervisor, ReviewDecision.REVISION_REQUESTED,
                comments="", items=[],
            )

    def test_corrections_may_be_pinned_to_a_page(self, under_review, supervisor):
        review, _ = submit_review(
            under_review, supervisor, ReviewDecision.REVISION_REQUESTED,
            comments="See the notes.",
            items=[
                {"page_number": 3, "body": "Objective 2 repeats objective 1."},
                {"page_number": 7, "body": "Name the dataset."},
            ],
        )
        assert review.items.count() == 2
        assert review.items.first().page_number == 3

    def test_only_this_monograph_s_supervisor_may_review_it(
        self, under_review, other_supervisor
    ):
        with pytest.raises(DomainError):
            submit_review(
                under_review, other_supervisor, ReviewDecision.APPROVED
            )

    def test_rounds_are_numbered_so_the_sequence_is_readable(
        self, under_review, supervisor, student
    ):
        from monographs.services.transitions import perform_transition

        first, _ = submit_review(
            under_review, supervisor, ReviewDecision.REVISION_REQUESTED,
            comments="Round one.",
        )
        under_review.refresh_from_db()
        perform_transition(under_review, student, S.PROPOSAL_SUBMITTED)
        under_review.refresh_from_db()
        perform_transition(under_review, supervisor, S.UNDER_REVIEW)
        under_review.refresh_from_db()

        second, _ = submit_review(
            under_review, supervisor, ReviewDecision.REVISION_REQUESTED,
            comments="Round two.",
        )
        assert (first.round_number, second.round_number) == (1, 2)


@pytest.mark.django_db
class TestReviewsAreNotRewritten:
    def test_a_review_cannot_be_edited_through_the_api(
        self, as_user, under_review, supervisor
    ):
        """Feedback a student has already read must not change underneath them."""
        review, _ = submit_review(
            under_review, supervisor, ReviewDecision.APPROVED, summary="Good."
        )
        response = as_user(supervisor).patch(
            f"/api/v1/reviews/{review.id}/", {"summary": "Actually, no."}, format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_a_review_cannot_be_deleted_through_the_api(
        self, as_user, under_review, supervisor
    ):
        review, _ = submit_review(
            under_review, supervisor, ReviewDecision.APPROVED, summary="Good."
        )
        response = as_user(supervisor).delete(f"/api/v1/reviews/{review.id}/")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
