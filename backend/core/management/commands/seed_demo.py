"""
Load a department's worth of believable data.

Used for demonstrations, for training staff before they touch real records,
and for getting a fresh checkout to a state where every screen has something
on it. Never run this against a live installation.
"""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import StudentProfile, SupervisorProfile, User
from archive.services.similarity import archive_monograph
from core.enums import (
    CommitteeRole, DefenseResult, DocumentType, MonographStage, ReviewDecision, Role,
)
from defenses.models import CommitteeMember, Defense
from documents.models import Document
from monographs.models import Monograph, MonographMember, StageTransition
from organization.models import (
    AcademicYear, Department, DepartmentPolicy, Faculty, ResearchArea, StageDeadline,
)
from reviews.models import Review, ReviewComment

PASSWORD = "TestPass123!"

STAFF = [
    ("hod001", "Ahmad Karimi", Role.HEAD_OF_DEPARTMENT, "Prof.", ""),
    ("sup001", "Fatima Noori", Role.SUPERVISOR, "Dr.", "Machine Learning"),
    ("sup002", "Rahim Wardak", Role.SUPERVISOR, "Dr.", "Networks and Security"),
    ("sup003", "Latifa Sherzai", Role.SUPERVISOR, "Dr.", "Software Engineering"),
    ("exm001", "Omar Sadat", Role.COMMITTEE_MEMBER, "Dr.", ""),
    ("exm002", "Nadia Faizi", Role.COMMITTEE_MEMBER, "Dr.", ""),
]

STUDENTS = [
    "Bilal Ahmadi", "Zahra Rahimi", "Nasir Hakimi", "Marium Sultani",
    "Javid Amiri", "Sara Popal", "Yusuf Stanikzai", "Farida Azimi",
    "Hamid Rasooli", "Palwasha Nazari", "Idris Safi", "Nargis Katawazai",
]

#: title, stage, supervisor index, area, days at that stage, grade
WORK = [
    ("Fraud Detection in Banking Networks Using Graph Neural Networks",
     MonographStage.UNDER_REVIEW, 0, 0, 12, None),
    ("Intrusion Detection for University Campus Networks",
     MonographStage.RESEARCH_IN_PROGRESS, 1, 1, 48, None),
    ("Predicting Student Performance with Machine Learning",
     MonographStage.PROPOSAL_SUBMITTED, 0, 0, 9, None),
    ("A Secure Messaging Protocol for Low Bandwidth Links",
     MonographStage.TOPIC_SUBMITTED, None, 1, 3, None),
    ("Automated Grading of Short Answer Questions",
     MonographStage.COMPLETED, 0, 0, 140, 82.5),
    ("Offline First Mobile Applications for Rural Areas",
     MonographStage.FINAL_REVIEW, 1, 2, 6, None),
    ("An Attendance System Using Face Recognition",
     MonographStage.REVISION_REQUIRED, 2, 0, 21, None),
    ("Comparing Database Engines for Low Resource Servers",
     MonographStage.PROPOSAL_APPROVED, 2, 2, 15, None),
    ("A Dari Language Spell Checker",
     MonographStage.RESEARCH_IN_PROGRESS, 0, 0, 67, None),
    ("Load Balancing Strategies for University Web Services",
     MonographStage.DRAFT, None, 1, 2, None),
    ("Digitising Student Records in Afghan Universities",
     MonographStage.COMPLETED, 1, 2, 160, 76.0),
    ("Detecting Plagiarism in Student Assignments",
     MonographStage.DEFENSE_SCHEDULED, 2, 0, 4, None),
]


class Command(BaseCommand):
    help = "Load a demonstration department. Do not run against real data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Remove existing demo records before loading.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(20260101)  # same data every run, so demos are repeatable

        if options["wipe"]:
            self._wipe()

        faculty, _ = Faculty.objects.get_or_create(
            code="CS", defaults={"name": "Computer Science"}
        )
        department, _ = Department.objects.get_or_create(
            code="SE", defaults={"faculty": faculty, "name": "Software Engineering"}
        )
        DepartmentPolicy.objects.get_or_create(department=department)

        year, _ = AcademicYear.objects.get_or_create(
            name="2025-2026",
            defaults={
                "start_date": date(2025, 9, 1),
                "end_date": date(2026, 6, 30),
                "is_current": True,
            },
        )

        areas = [
            ResearchArea.objects.get_or_create(department=department, name=name)[0]
            for name in ("Machine Learning", "Networks and Security", "Software Engineering")
        ]

        staff = self._create_staff(department)
        department.head = staff["hod001"]
        department.save()

        supervisors = [staff["sup001"], staff["sup002"], staff["sup003"]]
        students = self._create_students(department)

        self._create_deadlines(department, year)
        monographs = self._create_monographs(
            department, year, areas, supervisors, students
        )
        self._add_feedback(monographs, supervisors)
        self._add_defenses(monographs, staff, supervisors)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demonstration data loaded."))
        self.stdout.write("")
        self.stdout.write(f"  {User.objects.count()} people, "
                          f"{Monograph.objects.count()} monographs, "
                          f"{Defense.objects.count()} defences")
        self.stdout.write("")
        self.stdout.write("  Sign in with any of these:")
        self.stdout.write(f"    hod001   head of department   {PASSWORD}")
        self.stdout.write(f"    sup001   supervisor           {PASSWORD}")
        self.stdout.write(f"    stu001   student              {PASSWORD}")
        self.stdout.write(f"    exm001   committee member     {PASSWORD}")
        self.stdout.write("")

    # -- pieces ----------------------------------------------------------

    def _wipe(self):
        """
        Clear demonstration records.

        Order matters: an archive entry protects the monograph it describes,
        which is deliberate — a finished monograph must not vanish from the
        permanent library — so archive rows go first. Monographs are removed
        through all_objects because the default manager hides soft-deleted
        rows, which would otherwise be left behind.
        """
        from archive.models import ArchiveEntry, TopicSimilarity
        from monographs.models import ActivityLog

        self.stdout.write("Removing existing records…")

        # These models soft-delete by default, which only sets a flag — the
        # row and its protecting references would survive. Demonstration data
        # is meant to be genuinely thrown away, so go through the manager that
        # sees everything and delete for real.
        for model in (TopicSimilarity, ArchiveEntry, Review, Defense, Document,
                      ActivityLog, StageTransition, MonographMember, Monograph,
                      StageDeadline, ResearchArea):
            manager = getattr(model, "all_objects", model.objects)
            queryset = manager.all()
            hard = getattr(queryset, "hard_delete", None)
            (hard or queryset.delete)()

        StudentProfile.objects.all().delete()
        SupervisorProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _create_staff(self, department):
        people = {}
        for username, name, role, title, specialism in STAFF:
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User.objects.create_user(
                    username, PASSWORD, full_name=name, role=role,
                    department=department, title=title,
                )
            if user.can_supervise:
                SupervisorProfile.objects.get_or_create(
                    user=user,
                    defaults={"specialization": specialism, "max_students": 8},
                )
            people[username] = user
        return people

    def _create_students(self, department):
        students = []
        for index, name in enumerate(STUDENTS, start=1):
            username = f"stu{index:03d}"
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User.objects.create_user(
                    username, PASSWORD, full_name=name,
                    role=Role.STUDENT, department=department,
                )
            StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "student_id": f"CS-2021-{index:03d}",
                    "enrollment_year": 2021,
                    "program": "Bachelor of Software Engineering",
                },
            )
            students.append(user)
        return students

    def _create_deadlines(self, department, year):
        today = date.today()
        for stage, offset, description in (
            (MonographStage.TOPIC_APPROVED, -60, "Topics approved"),
            (MonographStage.PROPOSAL_APPROVED, -20, "Proposals approved"),
            (MonographStage.FINAL_SUBMISSION, 30, "Final monographs submitted"),
            (MonographStage.DEFENSE_SCHEDULED, 60, "Defences held"),
        ):
            StageDeadline.objects.get_or_create(
                department=department, academic_year=year, stage=stage,
                defaults={"due_date": today + timedelta(days=offset),
                          "description": description},
            )

    def _create_monographs(self, department, year, areas, supervisors, students):
        created = []
        for index, (title, stage, sup_index, area_index, days, grade) in enumerate(WORK):
            if Monograph.objects.filter(title=title).exists():
                created.append(Monograph.objects.get(title=title))
                continue

            student = students[index % len(students)]
            supervisor = supervisors[sup_index] if sup_index is not None else None
            moved = timezone.now() - timedelta(days=days)

            monograph = Monograph.objects.create(
                title=title,
                abstract=f"This study investigates {title.lower()}, with a "
                         f"practical evaluation against existing approaches.",
                objectives="Identify the problem clearly. Build a working "
                           "solution. Measure it against what is used today.",
                methodology="A literature review, an implementation, and an "
                            "empirical comparison using local data.",
                keywords=title.lower().split()[:4],
                department=department, academic_year=year,
                research_area=areas[area_index], supervisor=supervisor,
                stage=stage, created_by=student, final_grade=grade,
                stage_changed_at=moved,
                supervisor_assigned_at=moved if supervisor else None,
            )
            MonographMember.objects.create(
                monograph=monograph, student=student, is_lead=True
            )

            # A plausible history, so the timeline and the bottleneck report
            # have something real to work from.
            StageTransition.objects.create(
                monograph=monograph, from_stage=MonographStage.DRAFT,
                to_stage=MonographStage.TOPIC_SUBMITTED, actor=student,
                days_in_previous_stage=random.randint(2, 10),
            )
            if stage != MonographStage.TOPIC_SUBMITTED and stage != MonographStage.DRAFT:
                StageTransition.objects.create(
                    monograph=monograph, from_stage=MonographStage.TOPIC_SUBMITTED,
                    to_stage=MonographStage.TOPIC_APPROVED,
                    actor=department.head, days_in_previous_stage=random.randint(3, 14),
                )

            if stage not in (MonographStage.DRAFT, MonographStage.TOPIC_SUBMITTED):
                Document.objects.create(
                    monograph=monograph, document_type=DocumentType.PROPOSAL,
                    title="Research Proposal",
                )
            if stage in (MonographStage.FINAL_REVIEW, MonographStage.DEFENSE_SCHEDULED,
                         MonographStage.COMPLETED):
                Document.objects.create(
                    monograph=monograph, document_type=DocumentType.FINAL_MONOGRAPH,
                    title="Final Monograph",
                )

            created.append(monograph)
        return created

    def _add_feedback(self, monographs, supervisors):
        needing = [m for m in monographs
                   if m.stage == MonographStage.REVISION_REQUIRED and not m.reviews.exists()]
        for monograph in needing:
            review = Review.objects.create(
                monograph=monograph, reviewer=monograph.supervisor,
                decision=ReviewDecision.REVISION_REQUESTED,
                summary="Narrow the scope before you continue",
                comments="The objectives are too broad for one year of work. "
                         "Choose one and do it properly.",
            )
            ReviewComment.objects.create(
                review=review, page_number=3,
                body="Objective 2 repeats objective 1 in different words.",
            )
            ReviewComment.objects.create(
                review=review, page_number=7,
                body="Name the dataset you intend to use.",
            )

    def _add_defenses(self, monographs, staff, supervisors):
        for monograph in monographs:
            if hasattr(monograph, "defense"):
                continue

            if monograph.stage == MonographStage.COMPLETED:
                held = timezone.now() - timedelta(days=random.randint(20, 60))
                defense = Defense.objects.create(
                    monograph=monograph, scheduled_at=held, held_at=held,
                    location="Room 204, Main Building", duration_minutes=90,
                    result=DefenseResult.PASSED, supervisor_score=85,
                    notes="Well presented. The student answered confidently.",
                )
                for person, role, score in (
                    (staff["hod001"], CommitteeRole.CHAIR, 80),
                    (monograph.supervisor, CommitteeRole.SUPERVISOR, 78),
                    (staff["exm001"], CommitteeRole.INTERNAL_EXAMINER, 76),
                ):
                    CommitteeMember.objects.create(
                        defense=defense, member=person, role=role, score=score,
                        comments="Good work.", scored_at=held, has_read_monograph=True,
                    )
                defense.final_grade = defense.calculate_final_grade()
                defense.save()
                Monograph.objects.filter(pk=monograph.pk).update(
                    final_grade=defense.final_grade
                )
                archive_monograph(monograph, staff["hod001"])

            elif monograph.stage == MonographStage.DEFENSE_SCHEDULED:
                defense = Defense.objects.create(
                    monograph=monograph,
                    scheduled_at=timezone.now() + timedelta(days=random.randint(5, 20)),
                    location="Room 118", duration_minutes=60,
                )
                for person, role in (
                    (staff["hod001"], CommitteeRole.CHAIR),
                    (monograph.supervisor, CommitteeRole.SUPERVISOR),
                    (staff["exm002"], CommitteeRole.INTERNAL_EXAMINER),
                ):
                    CommitteeMember.objects.create(
                        defense=defense, member=person, role=role,
                        has_read_monograph=(role == CommitteeRole.CHAIR),
                    )
