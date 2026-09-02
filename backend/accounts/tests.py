"""Signing in, and who can see whom."""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestSignIn:
    def test_a_student_signs_in_with_their_university_id(self, api, student):
        response = api.post(
            "/api/v1/auth/login/",
            {"username": "stu001", "password": "TestPass123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        # The user travels back with the tokens so the app can render at once.
        assert response.data["user"]["full_name"] == "Bilal Ahmadi"

    def test_the_wrong_password_is_refused(self, api, student):
        response = api.post(
            "/api/v1/auth/login/",
            {"username": "stu001", "password": "wrong"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_an_inactive_account_cannot_sign_in(self, api, student):
        student.is_active = False
        student.save()
        response = api.post(
            "/api/v1/auth/login/",
            {"username": "stu001", "password": "TestPass123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_signing_in_needs_no_email_address(self, student):
        """Many students do not use email, so it must never be required."""
        assert student.email == ""
        assert student.is_active


@pytest.mark.django_db
class TestCapabilityFlags:
    def test_the_signed_in_person_is_told_what_they_may_do(self, as_user, hod):
        """The frontend renders its navigation from these."""
        response = as_user(hod).get("/api/v1/auth/me/")
        permissions = response.data["permissions"]
        assert permissions["is_head_of_department"]
        assert permissions["can_supervise"]
        assert not permissions["is_student"]

    def test_a_head_of_department_may_also_supervise(self, hod):
        assert hod.can_supervise


@pytest.mark.django_db
class TestSupervisorCapacity:
    def test_capacity_counts_only_unfinished_work(self, supervised, supervisor):
        from core.enums import MonographStage

        profile = supervisor.supervisor_profile
        assert profile.active_student_count == 1

        supervised.stage = MonographStage.COMPLETED
        supervised.save()
        assert profile.active_student_count == 0

    def test_someone_at_their_limit_is_reported_as_full(self, supervisor):
        profile = supervisor.supervisor_profile
        profile.max_students = 0
        profile.save()
        assert not profile.has_capacity

    def test_an_individual_limit_overrides_the_department_default(
        self, supervisor, policy
    ):
        policy.default_max_students_per_supervisor = 10
        policy.save()
        profile = supervisor.supervisor_profile

        assert profile.effective_max_students == 8  # their own limit

        profile.max_students = None
        profile.save()
        assert profile.effective_max_students == 10  # falls back to the department
