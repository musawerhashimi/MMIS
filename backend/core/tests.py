"""
Who can see what.

These are the tests that matter most for privacy: a student's draft is
private to the people working on it, and being handed a URL must not be
enough to read someone else's work.
"""
import pytest
from rest_framework import status

from core.enums import FINISHED_STAGES, MonographStage as S, stage_progress_percent
from monographs.models import Monograph, MonographMember


@pytest.fixture
def other_monograph(department, year, area, other_student):
    """A second monograph belonging to a different student entirely."""
    m = Monograph.objects.create(
        title="Someone Else's Research",
        department=department, academic_year=year, research_area=area,
        created_by=other_student,
    )
    MonographMember.objects.create(monograph=m, student=other_student, is_lead=True)
    return m


@pytest.mark.django_db
class TestVisibility:
    def test_a_student_sees_only_their_own_work(
        self, as_user, student, monograph, other_monograph
    ):
        response = as_user(student).get("/api/v1/monographs/")
        titles = [row["title"] for row in response.data["results"]]

        assert monograph.title in titles
        assert other_monograph.title not in titles

    def test_another_student_s_monograph_reads_as_missing(
        self, as_user, student, other_monograph
    ):
        """404 rather than 403 — its existence is not disclosed."""
        response = as_user(student).get(f"/api/v1/monographs/{other_monograph.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_a_supervisor_sees_their_own_students(
        self, as_user, supervisor, supervised, other_monograph
    ):
        response = as_user(supervisor).get("/api/v1/monographs/")
        titles = [row["title"] for row in response.data["results"]]

        assert supervised.title in titles
        assert other_monograph.title not in titles

    def test_a_head_of_department_sees_the_whole_department(
        self, as_user, hod, monograph, other_monograph
    ):
        response = as_user(hod).get("/api/v1/monographs/")
        titles = [row["title"] for row in response.data["results"]]

        assert monograph.title in titles
        assert other_monograph.title in titles

    def test_signing_in_is_required(self, api, monograph):
        response = api.get(f"/api/v1/monographs/{monograph.id}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestEditingRules:
    def test_a_student_may_edit_their_own_draft(self, monograph, student):
        assert monograph.is_editable_by(student)

    def test_a_submitted_topic_is_locked_to_the_student(self, monograph, student):
        """Nobody may quietly rewrite a topic that is awaiting a decision."""
        monograph.stage = S.TOPIC_SUBMITTED
        monograph.save()
        assert not monograph.is_editable_by(student)

    def test_a_returned_topic_becomes_editable_again(self, monograph, student):
        monograph.stage = S.REVISION_REQUIRED
        monograph.save()
        assert monograph.is_editable_by(student)

    def test_a_finished_monograph_is_closed_to_everyone(
        self, supervised, student, supervisor, hod
    ):
        supervised.stage = S.COMPLETED
        supervised.save()
        for person in (student, supervisor, hod):
            assert not supervised.is_editable_by(person)


@pytest.mark.django_db
class TestSoftDelete:
    def test_deleting_hides_a_record_without_destroying_it(self, monograph, hod):
        """Student work must survive; deletion is a flag, never a removal."""
        monograph.delete(deleted_by=hod)

        assert not Monograph.objects.filter(pk=monograph.pk).exists()
        assert Monograph.all_objects.filter(pk=monograph.pk).exists()

        monograph.refresh_from_db()
        assert monograph.is_deleted
        assert monograph.deleted_by == hod

    def test_a_deleted_record_can_be_brought_back(self, monograph, hod):
        monograph.delete(deleted_by=hod)
        monograph.restore()
        assert Monograph.objects.filter(pk=monograph.pk).exists()


class TestProgress:
    def test_a_draft_has_made_no_progress(self):
        assert stage_progress_percent(S.DRAFT) == 0

    def test_a_completed_monograph_is_finished(self):
        assert stage_progress_percent(S.COMPLETED) == 100

    def test_progress_rises_along_the_journey(self):
        ladder = [
            S.DRAFT, S.TOPIC_SUBMITTED, S.TOPIC_APPROVED, S.PROPOSAL_APPROVED,
            S.RESEARCH_IN_PROGRESS, S.DEFENSE_SCHEDULED, S.COMPLETED,
        ]
        values = [stage_progress_percent(stage) for stage in ladder]
        assert values == sorted(values)

    def test_an_ended_monograph_shows_no_progress(self):
        """Rejected and withdrawn sit outside the ladder."""
        for stage in (S.REJECTED, S.WITHDRAWN):
            assert stage_progress_percent(stage) == 0
            assert stage in FINISHED_STAGES


@pytest.mark.django_db
class TestErrorShape:
    def test_failures_arrive_in_one_consistent_envelope(self, as_user, student, monograph):
        """The frontend has a single error handler, so the shape must not vary."""
        response = as_user(student).post(
            f"/api/v1/monographs/{monograph.id}/transition/",
            {"target": "completed"},
            format="json",
        )
        assert response.status_code >= 400
        assert "error" in response.data
        assert {"code", "message", "details"} <= set(response.data["error"])

    def test_the_message_explains_what_to_do(self, as_user, hod, monograph):
        monograph.stage = S.TOPIC_SUBMITTED
        monograph.save()

        response = as_user(hod).post(
            f"/api/v1/monographs/{monograph.id}/transition/",
            {"target": "topic_approved"},
            format="json",
        )
        assert "supervisor" in response.data["error"]["message"].lower()


@pytest.mark.django_db
class TestHealth:
    def test_the_liveness_probe_needs_no_credentials(self, api):
        """The university server runs unattended; this must always answer."""
        response = api.get("/api/health/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"
