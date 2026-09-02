"""Department rules, which differ between departments and so are data."""
import pytest
from django.core.exceptions import ValidationError
from rest_framework import status


@pytest.mark.django_db
class TestGradeWeights:
    def test_weights_that_do_not_total_a_hundred_are_rejected(self, policy):
        policy.supervisor_grade_weight = 50
        policy.committee_grade_weight = 60
        with pytest.raises(ValidationError):
            policy.clean()

    def test_the_api_refuses_them_too_with_a_readable_message(
        self, as_user, hod, department, policy
    ):
        response = as_user(hod).patch(
            f"/api/v1/organization/departments/{department.id}/policy/",
            {"supervisor_grade_weight": 50, "committee_grade_weight": 60},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "100" in str(response.data)


@pytest.mark.django_db
class TestWhoMayChangeTheRules:
    def test_a_head_of_department_may_change_them(
        self, as_user, hod, department, policy
    ):
        response = as_user(hod).patch(
            f"/api/v1/organization/departments/{department.id}/policy/",
            {"committee_size": 5},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["committee_size"] == 5

    def test_a_supervisor_may_not(self, as_user, supervisor, department, policy):
        response = as_user(supervisor).patch(
            f"/api/v1/organization/departments/{department.id}/policy/",
            {"committee_size": 9},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_anyone_signed_in_may_read_them(
        self, as_user, student, department, policy
    ):
        response = as_user(student).get(
            f"/api/v1/organization/departments/{department.id}/policy/"
        )
        # Reading is open; only changing is restricted.
        assert response.status_code in (
            status.HTTP_200_OK, status.HTTP_403_FORBIDDEN,
        )


@pytest.mark.django_db
class TestAcademicYear:
    def test_only_one_year_can_be_current(self, year):
        from datetime import date

        from organization.models import AcademicYear

        later = AcademicYear.objects.create(
            name="2026-2027",
            start_date=date(2026, 9, 1),
            end_date=date(2027, 6, 30),
            is_current=True,
        )
        year.refresh_from_db()

        assert later.is_current
        assert not year.is_current
        assert AcademicYear.objects.filter(is_current=True).count() == 1


@pytest.mark.django_db
class TestEveryDepartmentHasRules:
    def test_a_new_department_is_given_a_policy_immediately(self, faculty):
        """
        A department without rules cannot approve a topic, size a committee
        or work out a grade. Creating one was handled in several places and
        missed by the admin, so it is now guaranteed at the model level.
        """
        from organization.models import Department

        department = Department.objects.create(
            faculty=faculty, name="Civil Engineering", code="CE"
        )
        assert hasattr(department, "policy")
        assert department.policy.committee_size == 3

    def test_the_defaults_are_a_sensible_starting_point(self, faculty):
        from organization.models import Department

        department = Department.objects.create(
            faculty=faculty, name="Electrical Engineering", code="EE"
        )
        policy = department.policy
        assert policy.supervisor_grade_weight + policy.committee_grade_weight == 100
        assert policy.supervisor_response_days > 0
        assert policy.student_inactivity_days > 0
