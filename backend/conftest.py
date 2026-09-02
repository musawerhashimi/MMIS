"""
Shared fixtures.

Builds one small department with a person in every role, because almost
every test needs the same cast and setting it up per test would bury what
each test is actually checking.
"""
from datetime import date

import pytest
from django.utils import timezone

from accounts.models import StudentProfile, SupervisorProfile, User
from core.enums import Role
from monographs.models import Monograph, MonographMember
from organization.models import (
    AcademicYear, Department, DepartmentPolicy, Faculty, ResearchArea,
)


@pytest.fixture
def faculty(db):
    return Faculty.objects.create(name="Computer Science", code="CS")


@pytest.fixture
def department(faculty):
    return Department.objects.create(
        faculty=faculty, name="Software Engineering", code="SE"
    )


@pytest.fixture
def policy(department):
    """
    The department's rules.

    Every department is given a policy the moment it is created, so this
    hands back the existing one rather than making a second.
    """
    return DepartmentPolicy.objects.get(department=department)


@pytest.fixture
def year(db):
    return AcademicYear.objects.create(
        name="2025-2026",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 6, 30),
        is_current=True,
    )


@pytest.fixture
def area(department):
    return ResearchArea.objects.create(department=department, name="Machine Learning")


def _user(username, name, role, department, **extra):
    return User.objects.create_user(
        username, "TestPass123!", full_name=name, role=role,
        department=department, **extra,
    )


@pytest.fixture
def hod(department, policy):
    user = _user("hod001", "Ahmad Karimi", Role.HEAD_OF_DEPARTMENT, department, title="Prof.")
    department.head = user
    department.save()
    return user


@pytest.fixture
def supervisor(department):
    user = _user("sup001", "Fatima Noori", Role.SUPERVISOR, department, title="Dr.")
    SupervisorProfile.objects.create(user=user, max_students=8)
    return user


@pytest.fixture
def other_supervisor(department):
    user = _user("sup002", "Rahim Wardak", Role.SUPERVISOR, department, title="Dr.")
    SupervisorProfile.objects.create(user=user, max_students=6)
    return user


@pytest.fixture
def examiner(department):
    return _user("exm001", "Omar Sadat", Role.COMMITTEE_MEMBER, department, title="Dr.")


@pytest.fixture
def student(department):
    user = _user("stu001", "Bilal Ahmadi", Role.STUDENT, department)
    StudentProfile.objects.create(user=user, student_id="CS-2021-001")
    return user


@pytest.fixture
def other_student(department):
    """A student with no connection to the monograph under test."""
    user = _user("stu999", "Outsider Student", Role.STUDENT, department)
    StudentProfile.objects.create(user=user, student_id="CS-2021-999")
    return user


@pytest.fixture
def admin_user(department):
    return _user("admin001", "System Administrator", Role.ADMIN, department,
                 is_staff=True, is_superuser=True)


@pytest.fixture
def monograph(department, year, area, student, policy):
    """A draft monograph authored by `student`, with no supervisor yet."""
    m = Monograph.objects.create(
        title="Fraud Detection Using Graph Neural Networks",
        abstract="Detecting fraudulent transactions with graph models.",
        department=department, academic_year=year, research_area=area,
        created_by=student,
    )
    MonographMember.objects.create(monograph=m, student=student, is_lead=True)
    return m


@pytest.fixture
def supervised(monograph, supervisor):
    """The same monograph, with a supervisor assigned."""
    monograph.supervisor = supervisor
    monograph.supervisor_assigned_at = timezone.now()
    monograph.save()
    return monograph


@pytest.fixture
def api(db):
    """An unauthenticated DRF client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def as_user(api):
    """Sign the client in as a given user."""

    def _sign_in(user):
        api.force_authenticate(user=user)
        return api

    return _sign_in
