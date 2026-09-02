"""
The rules of the monograph journey.

These lock down the behaviour the whole product depends on: that a monograph
cannot skip a stage, that role alone never grants permission, and that every
move leaves a record nothing can rewrite.
"""
import pytest
from django.utils import timezone

from core.enums import DocumentType, MonographStage as S
from core.exceptions import InvalidStageTransition, WorkflowPermissionDenied
from documents.models import Document
from monographs import workflow
from monographs.models import Monograph, StageTransition
from monographs.services.transitions import perform_transition


# ---------------------------------------------------------------------------
# The shape of the journey
# ---------------------------------------------------------------------------

class TestWorkflowGraph:
    def test_every_stage_is_reachable_from_draft(self):
        """No stage may be stranded — a monograph must be able to reach each."""
        reachable = {S.DRAFT}
        frontier = [S.DRAFT]
        while frontier:
            current = frontier.pop()
            for move in workflow.transitions_from(current):
                if move.target not in reachable:
                    reachable.add(move.target)
                    frontier.append(move.target)

        every_stage = {value for value, _label in S.choices}
        assert every_stage - reachable == set()

    def test_only_terminal_stages_are_dead_ends(self):
        """A monograph must never get stuck somewhere it cannot leave."""
        terminal = {S.COMPLETED, S.REJECTED, S.WITHDRAWN}
        for value, _label in S.choices:
            has_exit = bool(workflow.transitions_from(value))
            assert has_exit is (value not in terminal), value

    def test_revision_loop_returns_to_review(self):
        """
        The revision cycle in the requirements must actually close: work goes
        back to the student and can come round again any number of times.
        """
        assert workflow.get_transition(S.UNDER_REVIEW, S.REVISION_REQUIRED)
        assert workflow.get_transition(S.REVISION_REQUIRED, S.PROPOSAL_SUBMITTED)
        assert workflow.get_transition(S.PROPOSAL_SUBMITTED, S.UNDER_REVIEW)

    def test_rejections_and_revisions_demand_an_explanation(self):
        """Nobody may be told 'no' without being told why."""
        for move in workflow.TRANSITIONS:
            if move.target in (S.REJECTED, S.WITHDRAWN, S.REVISION_REQUIRED):
                assert move.requires_note, f"{move.source} -> {move.target}"


# ---------------------------------------------------------------------------
# Who may do what
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPermissions:
    def test_student_cannot_approve_their_own_topic(self, monograph, student, supervisor):
        monograph.supervisor = supervisor
        monograph.stage = S.TOPIC_SUBMITTED
        monograph.save()

        with pytest.raises(WorkflowPermissionDenied):
            perform_transition(monograph, student, S.TOPIC_APPROVED)

    def test_a_supervisor_may_only_act_on_their_own_students(
        self, supervised, other_supervisor
    ):
        """Holding the supervisor role is not enough — it must be this monograph's."""
        supervised.stage = S.PROPOSAL_SUBMITTED
        supervised.save()

        with pytest.raises(WorkflowPermissionDenied):
            perform_transition(supervised, other_supervisor, S.UNDER_REVIEW)

    def test_an_unrelated_student_cannot_touch_the_monograph(
        self, monograph, other_student
    ):
        with pytest.raises((WorkflowPermissionDenied, InvalidStageTransition)):
            perform_transition(monograph, other_student, S.TOPIC_SUBMITTED)

    def test_an_administrator_may_act_anywhere(self, monograph, admin_user):
        record = perform_transition(monograph, admin_user, S.TOPIC_SUBMITTED)
        assert record.to_stage == S.TOPIC_SUBMITTED

    def test_available_actions_never_offer_a_move_the_server_would_refuse(
        self, supervised, student, supervisor, hod
    ):
        """
        The buttons on screen come from this list, so anything it offers must
        actually succeed.
        """
        supervised.stage = S.UNDER_REVIEW
        supervised.save()

        for actor in (student, supervisor, hod):
            for move in workflow.available_transitions(supervised, actor):
                allowed, reason = workflow.can_transition(supervised, actor, move.target)
                assert allowed, f"{actor.role} was offered {move.target}: {reason}"


# ---------------------------------------------------------------------------
# Conditions that must hold before a move
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGuards:
    def test_a_topic_cannot_be_approved_without_a_supervisor(self, monograph, hod):
        monograph.stage = S.TOPIC_SUBMITTED
        monograph.save()

        with pytest.raises(InvalidStageTransition) as raised:
            perform_transition(monograph, hod, S.TOPIC_APPROVED)
        assert "supervisor" in str(raised.value.detail).lower()

    def test_a_proposal_cannot_be_submitted_without_the_document(
        self, supervised, student
    ):
        supervised.stage = S.TOPIC_APPROVED
        supervised.save()

        with pytest.raises(InvalidStageTransition) as raised:
            perform_transition(supervised, student, S.PROPOSAL_SUBMITTED)
        assert "upload" in str(raised.value.detail).lower()

    def test_the_same_move_succeeds_once_the_document_exists(
        self, supervised, student
    ):
        supervised.stage = S.TOPIC_APPROVED
        supervised.save()
        Document.objects.create(
            monograph=supervised, document_type=DocumentType.PROPOSAL, title="Proposal"
        )

        record = perform_transition(supervised, student, S.PROPOSAL_SUBMITTED)
        assert record.to_stage == S.PROPOSAL_SUBMITTED

    def test_a_defence_cannot_be_scheduled_without_a_committee(self, supervised, hod):
        supervised.stage = S.FINAL_REVIEW
        supervised.save()

        with pytest.raises(InvalidStageTransition):
            perform_transition(supervised, hod, S.DEFENSE_SCHEDULED)

    def test_a_written_reason_is_required_to_request_revisions(
        self, supervised, supervisor
    ):
        supervised.stage = S.UNDER_REVIEW
        supervised.save()

        with pytest.raises(InvalidStageTransition) as raised:
            perform_transition(supervised, supervisor, S.REVISION_REQUIRED, note="")
        assert "explanation" in str(raised.value.detail).lower()


# ---------------------------------------------------------------------------
# Illegal moves
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestIllegalMoves:
    def test_a_stage_cannot_be_skipped(self, supervised, hod):
        with pytest.raises(InvalidStageTransition):
            perform_transition(supervised, hod, S.COMPLETED)

    def test_a_finished_monograph_cannot_be_moved(self, supervised, hod):
        supervised.stage = S.COMPLETED
        supervised.save()

        with pytest.raises(InvalidStageTransition):
            perform_transition(supervised, hod, S.DEFENDED)

    def test_a_withdrawn_monograph_offers_no_further_actions(
        self, supervised, student
    ):
        supervised.stage = S.WITHDRAWN
        supervised.save()
        assert workflow.available_transitions(supervised, student) == []


# ---------------------------------------------------------------------------
# The permanent record
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestHistory:
    def test_creating_a_monograph_records_its_first_stage(self, monograph):
        """Otherwise the timeline would appear to start at the second stage."""
        assert monograph.transitions.count() == 1
        assert monograph.transitions.first().to_stage == S.DRAFT

    def test_every_move_is_recorded_with_who_and_when(self, monograph, student):
        before = monograph.transitions.count()
        perform_transition(monograph, student, S.TOPIC_SUBMITTED, note="Ready.")

        assert monograph.transitions.count() == before + 1
        record = monograph.transitions.order_by("-created_at").first()
        assert record.from_stage == S.DRAFT
        assert record.to_stage == S.TOPIC_SUBMITTED
        assert record.actor == student
        assert record.note == "Ready."

    def test_a_refused_move_leaves_no_trace(self, monograph, other_student):
        """A failed attempt must not pollute the record."""
        before = monograph.transitions.count()
        with pytest.raises((WorkflowPermissionDenied, InvalidStageTransition)):
            perform_transition(monograph, other_student, S.TOPIC_SUBMITTED)
        assert monograph.transitions.count() == before

    def test_time_spent_at_each_stage_is_measured(self, monograph, student):
        """The 'where is the bottleneck' report reads this figure."""
        from datetime import timedelta

        Monograph.objects.filter(pk=monograph.pk).update(
            stage_changed_at=timezone.now() - timedelta(days=5)
        )
        monograph.refresh_from_db()

        record = perform_transition(monograph, student, S.TOPIC_SUBMITTED)
        assert record.days_in_previous_stage == 5

    def test_a_terminal_stage_always_carries_its_reason(self, monograph, student):
        perform_transition(
            monograph, student, S.WITHDRAWN, note="Changing to a different topic."
        )
        monograph.refresh_from_db()
        assert monograph.closure_reason == "Changing to a different topic."


# ---------------------------------------------------------------------------
# The journey end to end
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFullJourney:
    def test_a_monograph_travels_from_draft_to_completed(
        self, supervised, student, supervisor, hod, examiner, policy
    ):
        from core.enums import CommitteeRole, DefenseResult
        from defenses.models import CommitteeMember, Defense

        m = supervised

        def move(actor, target, note=""):
            """Move, then refresh — the service re-reads the row it locks."""
            record = perform_transition(m, actor, target, note=note)
            m.refresh_from_db()
            return record

        move(student, S.TOPIC_SUBMITTED)
        move(hod, S.TOPIC_APPROVED)

        Document.objects.create(
            monograph=m, document_type=DocumentType.PROPOSAL, title="Proposal"
        )
        move(student, S.PROPOSAL_SUBMITTED)
        move(supervisor, S.UNDER_REVIEW)

        # Round one comes back for changes, then the student submits again.
        move(supervisor, S.REVISION_REQUIRED, note="Narrow the scope.")
        move(student, S.PROPOSAL_SUBMITTED)
        move(supervisor, S.UNDER_REVIEW)
        move(supervisor, S.PROPOSAL_APPROVED)

        move(student, S.RESEARCH_IN_PROGRESS)
        Document.objects.create(
            monograph=m, document_type=DocumentType.FINAL_MONOGRAPH, title="Final"
        )
        move(student, S.FINAL_SUBMISSION)
        move(supervisor, S.FINAL_REVIEW)

        defense = Defense.objects.create(
            monograph=m, scheduled_at=timezone.now(), location="Room 204"
        )
        for person, role in (
            (hod, CommitteeRole.CHAIR),
            (supervisor, CommitteeRole.SUPERVISOR),
            (examiner, CommitteeRole.INTERNAL_EXAMINER),
        ):
            CommitteeMember.objects.create(defense=defense, member=person, role=role)

        move(hod, S.DEFENSE_SCHEDULED)

        for seat in defense.committee.all():
            seat.record_score(78)

        move(hod, S.DEFENDED)

        defense.supervisor_score = 85
        defense.result = DefenseResult.PASSED
        defense.final_grade = defense.calculate_final_grade()
        defense.save()
        Monograph.objects.filter(pk=m.pk).update(final_grade=defense.final_grade)
        m.refresh_from_db()

        move(hod, S.COMPLETED)

        m.refresh_from_db()
        assert m.stage == S.COMPLETED
        assert m.progress_percent == 100
        # 40% of 85 plus 60% of 78.
        assert str(m.final_grade) == "80.80"
        # Every move above, plus the row written when the monograph was created.
        assert m.transitions.count() == 15
