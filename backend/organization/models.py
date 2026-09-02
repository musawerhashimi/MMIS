"""
The university structure the monograph process hangs off: faculties,
departments, academic years, and the per-department rules.

The rules live in DepartmentPolicy rather than in code because they were
confirmed to differ between departments — who approves a topic, how a
supervisor is chosen, how many students one supervisor may carry, and how the
final grade is weighted. Changing them must never require a deployment.
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.enums import SupervisorAssignmentMode, TopicApprovalMode
from core.models import BaseModel


class Faculty(BaseModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "faculties"

    def __str__(self):
        return self.name


class Department(BaseModel):
    faculty = models.ForeignKey(
        Faculty, on_delete=models.PROTECT, related_name="departments"
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)

    head = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
    )

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["faculty", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_department_name_per_faculty",
            )
        ]

    def __str__(self):
        return self.name


class DepartmentPolicy(BaseModel):
    """
    How one department runs its monograph process.

    Every question from the requirements that turned out to vary between
    departments is a field here.
    """

    department = models.OneToOneField(
        Department, on_delete=models.CASCADE, related_name="policy"
    )

    # -- Topic approval ---------------------------------------------------
    topic_approval_mode = models.CharField(
        max_length=20,
        choices=TopicApprovalMode.choices,
        default=TopicApprovalMode.HEAD_ONLY,
    )
    topic_approval_votes_required = models.PositiveIntegerField(
        default=1,
        help_text="Approvals needed when the mode is committee vote.",
    )

    # -- Supervisor assignment --------------------------------------------
    supervisor_assignment_mode = models.CharField(
        max_length=20,
        choices=SupervisorAssignmentMode.choices,
        default=SupervisorAssignmentMode.ASSIGNED_BY_HEAD,
    )
    default_max_students_per_supervisor = models.PositiveIntegerField(default=10)

    # -- Group work --------------------------------------------------------
    allow_group_monographs = models.BooleanField(default=True)
    max_students_per_monograph = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
    )

    # -- Defense committee -------------------------------------------------
    committee_size = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )

    # -- Grade weighting ---------------------------------------------------
    # Stored as percentages that must add up to 100. The supervisor's mark and
    # the committee's average are combined using these weights.
    supervisor_grade_weight = models.PositiveIntegerField(
        default=40, validators=[MaxValueValidator(100)]
    )
    committee_grade_weight = models.PositiveIntegerField(
        default=60, validators=[MaxValueValidator(100)]
    )
    passing_grade = models.DecimalField(max_digits=5, decimal_places=2, default=60)

    # -- Deadlines ---------------------------------------------------------
    # Whether the department enforces one shared calendar or lets each
    # supervisor set dates per student.
    use_fixed_stage_deadlines = models.BooleanField(default=True)
    # How long a supervisor may sit on a submission before it is flagged as
    # overdue on the dashboard.
    supervisor_response_days = models.PositiveIntegerField(default=7)
    # How long a student may be inactive before being flagged as "gone quiet".
    student_inactivity_days = models.PositiveIntegerField(default=30)

    # -- Duplicate topic checking ------------------------------------------
    # Tuned against real title pairs: genuine duplicates worded differently
    # score around 65, merely related topics around 10. 60 catches the former
    # without flooding the head of department with the latter.
    similarity_threshold = models.PositiveIntegerField(
        default=60,
        validators=[MaxValueValidator(100)],
        help_text="Percent similarity above which a topic is flagged as a possible duplicate.",
    )

    class Meta:
        verbose_name_plural = "department policies"

    def __str__(self):
        return f"Policy for {self.department.name}"

    def clean(self):
        from django.core.exceptions import ValidationError

        total = self.supervisor_grade_weight + self.committee_grade_weight
        if total != 100:
            raise ValidationError(
                {"supervisor_grade_weight": f"Grade weights must add up to 100 (currently {total})."}
            )


class AcademicYear(BaseModel):
    """
    One monograph cycle.

    Exactly one year is current at a time; new monographs attach to it and
    dashboards default to it.
    """

    name = models.CharField(max_length=64, unique=True, help_text="For example 2025-2026.")
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, db_index=True)
    is_closed = models.BooleanField(
        default=False,
        help_text="A closed year is read-only; no new submissions are accepted.",
    )

    class Meta:
        ordering = ("-start_date",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Only one year may be current.
        if self.is_current:
            AcademicYear.objects.exclude(pk=self.pk).filter(is_current=True).update(
                is_current=False
            )
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.filter(is_current=True).first()


class StageDeadline(BaseModel):
    """
    A department's target date for reaching a given stage in a given year.

    Used to answer "who is behind schedule" without a supervisor having to
    track it manually.
    """

    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="stage_deadlines"
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE, related_name="stage_deadlines"
    )
    stage = models.CharField(max_length=32, db_index=True)
    due_date = models.DateField()
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("due_date",)
        constraints = [
            models.UniqueConstraint(
                fields=["department", "academic_year", "stage"],
                condition=models.Q(is_deleted=False),
                name="unique_deadline_per_stage",
            )
        ]

    def __str__(self):
        return f"{self.department.code} {self.stage} due {self.due_date}"


class ResearchArea(BaseModel):
    """
    Subject areas a monograph can belong to.

    Kept as data rather than a fixed list so a department can add its own
    without a code change, and so the archive can be browsed by area.
    """

    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="research_areas"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["department", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_research_area_per_department",
            )
        ]

    def __str__(self):
        return self.name
