"""Committees, scoring, and how the final grade is worked out."""
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from core.enums import CommitteeRole, DefenseResult
from defenses.models import CommitteeMember, Defense


@pytest.fixture
def defense(supervised, hod, supervisor, examiner):
    d = Defense.objects.create(
        monograph=supervised, scheduled_at=timezone.now(), location="Room 204"
    )
    for person, role in (
        (hod, CommitteeRole.CHAIR),
        (supervisor, CommitteeRole.SUPERVISOR),
        (examiner, CommitteeRole.INTERNAL_EXAMINER),
    ):
        CommitteeMember.objects.create(defense=d, member=person, role=role)
    return d


@pytest.mark.django_db
class TestGrading:
    def test_the_grade_uses_the_department_weights(self, defense, policy):
        """40% of the supervisor's mark, 60% of the committee average."""
        for seat in defense.committee.all():
            seat.record_score(78)
        defense.supervisor_score = Decimal("85")
        defense.save()

        assert defense.committee_average == Decimal("78.00")
        assert defense.calculate_final_grade() == Decimal("80.80")

    def test_changing_the_weights_changes_the_grade(self, defense, policy):
        for seat in defense.committee.all():
            seat.record_score(78)
        defense.supervisor_score = Decimal("85")
        defense.save()

        policy.supervisor_grade_weight = 60
        policy.committee_grade_weight = 40
        policy.save()
        defense.monograph.department.refresh_from_db()

        assert defense.calculate_final_grade() == Decimal("82.20")

    def test_the_committee_average_ignores_anyone_who_has_not_scored(self, defense):
        seats = list(defense.committee.all())
        seats[0].record_score(80)
        seats[1].record_score(70)
        # The third has not scored.
        assert defense.committee_average == Decimal("75.00")
        assert not defense.all_scores_in

    def test_a_grade_can_be_worked_out_from_the_committee_alone(self, defense, policy):
        """Some departments do not use a separate supervisor mark."""
        for seat in defense.committee.all():
            seat.record_score(72)
        assert defense.supervisor_score is None
        assert defense.calculate_final_grade() == Decimal("72.00")

    def test_the_suggested_result_follows_the_passing_grade(self, defense, policy):
        for seat in defense.committee.all():
            seat.record_score(45)
        defense.final_grade = defense.calculate_final_grade()
        defense.save()
        assert defense.derive_result() == DefenseResult.FAILED

        for seat in defense.committee.all():
            seat.record_score(75)
        defense.final_grade = defense.calculate_final_grade()
        defense.save()
        assert defense.derive_result() == DefenseResult.PASSED


@pytest.mark.django_db
class TestScoring:
    def test_a_committee_member_enters_their_own_score(self, as_user, defense, examiner):
        response = as_user(examiner).post(
            f"/api/v1/defenses/{defense.id}/score/",
            {"score": "77", "comments": "Solid work."},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["committee_member"]["score"] == "77.00"

    def test_someone_not_on_the_committee_cannot_score(
        self, as_user, defense, student
    ):
        response = as_user(student).post(
            f"/api/v1/defenses/{defense.id}/score/", {"score": "99"}, format="json",
        )
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND,
        )

    def test_a_result_cannot_be_recorded_while_scores_are_missing(
        self, as_user, defense, hod
    ):
        defense.committee.first().record_score(80)

        response = as_user(hod).post(
            f"/api/v1/defenses/{defense.id}/record_result/",
            {"result": "passed"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "score" in str(response.data).lower()

    def test_the_result_is_recorded_once_every_score_is_in(
        self, as_user, defense, hod, policy
    ):
        for seat in defense.committee.all():
            seat.record_score(78)

        response = as_user(hod).post(
            f"/api/v1/defenses/{defense.id}/record_result/",
            {"result": "passed", "supervisor_score": "85"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["final_grade"] == "80.80"

        defense.monograph.refresh_from_db()
        assert str(defense.monograph.final_grade) == "80.80"


@pytest.mark.django_db
class TestScheduling:
    def test_a_committee_smaller_than_the_policy_is_refused(
        self, as_user, hod, supervised, supervisor, policy
    ):
        policy.committee_size = 3
        policy.save()

        response = as_user(hod).post(
            "/api/v1/defenses/schedule/",
            {
                "monograph": str(supervised.id),
                "scheduled_at": timezone.now().isoformat(),
                "location": "Room 204",
                "committee": [{"member_id": str(supervisor.id), "role": "supervisor"}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "3" in str(response.data)

    def test_the_same_person_cannot_sit_twice(
        self, as_user, hod, supervised, supervisor
    ):
        response = as_user(hod).post(
            "/api/v1/defenses/schedule/",
            {
                "monograph": str(supervised.id),
                "scheduled_at": timezone.now().isoformat(),
                "committee": [
                    {"member_id": str(supervisor.id), "role": "supervisor"},
                    {"member_id": str(supervisor.id), "role": "internal"},
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
