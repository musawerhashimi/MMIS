"""
The monograph record and its permanent history.

This is the spine of the system. A monograph always sits at exactly one
stage, it can only move along legal transitions, and every move is written
into an append-only history that nothing in the codebase is allowed to edit
or delete.
"""
from django.db import models
from django.utils import timezone

from core.enums import (
    FINISHED_STAGES,
    MonographStage,
    stage_progress_percent,
)
from core.models import BaseModel


class MonographQuerySet(models.QuerySet):
    def active(self):
        """Monographs still moving through the process."""
        return self.exclude(stage__in=FINISHED_STAGES)

    def completed(self):
        return self.filter(stage=MonographStage.COMPLETED)

    def for_year(self, academic_year):
        return self.filter(academic_year=academic_year)

    def for_department(self, department):
        return self.filter(department=department)

    def supervised_by(self, user):
        return self.filter(supervisor=user)

    def authored_by(self, user):
        return self.filter(members__student=user)

    def awaiting_supervisor(self):
        """Submitted work that a supervisor has not yet answered."""
        return self.filter(
            stage__in=[
                MonographStage.PROPOSAL_SUBMITTED,
                MonographStage.UNDER_REVIEW,
                MonographStage.FINAL_SUBMISSION,
                MonographStage.FINAL_REVIEW,
            ]
        )

    def visible_to(self, user):
        """
        Every monograph this person is allowed to see.

        Someone not signed in sees nothing. Stated explicitly because the
        schema generator walks these querysets with an anonymous user, and
        because it is the right answer either way.
        """
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_admin:
            return self
        if user.is_head_of_department:
            return self.filter(department__in=user.headed_departments.all())
        if user.can_supervise:
            return self.filter(
                models.Q(supervisor=user) | models.Q(defense__committee__member=user)
            ).distinct()
        if user.is_committee_member:
            return self.filter(defense__committee__member=user).distinct()
        return self.filter(members__student=user).distinct()


class MonographManager(models.Manager.from_queryset(MonographQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Monograph(BaseModel):
    """One student project, from first idea to archived final copy."""

    title = models.CharField(max_length=500)
    abstract = models.TextField(blank=True)
    keywords = models.JSONField(default=list, blank=True)

    objectives = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    expected_outcome = models.TextField(blank=True)

    department = models.ForeignKey(
        "organization.Department", on_delete=models.PROTECT, related_name="monographs"
    )
    academic_year = models.ForeignKey(
        "organization.AcademicYear", on_delete=models.PROTECT, related_name="monographs"
    )
    research_area = models.ForeignKey(
        "organization.ResearchArea",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="monographs",
    )

    supervisor = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervised_monographs",
    )
    supervisor_assigned_at = models.DateTimeField(null=True, blank=True)

    stage = models.CharField(
        max_length=32,
        choices=MonographStage.choices,
        default=MonographStage.DRAFT,
        db_index=True,
    )
    stage_changed_at = models.DateTimeField(default=timezone.now)

    # Why a monograph was rejected or withdrawn. Terminal states must always
    # carry an explanation.
    closure_reason = models.TextField(blank=True)

    # Filled in when the process finishes.
    final_grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = MonographManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["department", "academic_year", "stage"]),
            models.Index(fields=["supervisor", "stage"]),
            models.Index(fields=["stage", "stage_changed_at"]),
        ]

    def __str__(self):
        return self.title

    # -- Derived state -----------------------------------------------------

    @property
    def progress_percent(self) -> int:
        return stage_progress_percent(self.stage)

    @property
    def is_finished(self) -> bool:
        return self.stage in FINISHED_STAGES

    @property
    def days_in_current_stage(self) -> int:
        return (timezone.now() - self.stage_changed_at).days

    @property
    def student_names(self) -> list[str]:
        return [m.student.full_name for m in self.members.all()]

    @property
    def policy(self):
        return getattr(self.department, "policy", None)

    # -- Access ------------------------------------------------------------

    def is_visible_to(self, user) -> bool:
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        if self.supervisor_id == user.id:
            return True
        if user.is_head_of_department and self.department_id in user.headed_departments.values_list(
            "id", flat=True
        ):
            return True
        if self.members.filter(student=user).exists():
            return True
        return self.is_on_committee(user)

    def is_on_committee(self, user) -> bool:
        """Whether this person sits on the monograph's defense committee."""
        defense = getattr(self, "defense", None)
        if defense is None:
            return False
        return defense.committee.filter(member=user).exists()

    def is_editable_by(self, user) -> bool:
        """
        Who may change the monograph record itself.

        A student owns the record only while the topic is still a draft or has
        come back for revision. Once submitted it is locked so nobody can
        quietly rewrite a topic that has already been approved.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_admin:
            return True
        if self.is_finished:
            return False
        if self.members.filter(student=user).exists():
            return self.stage in (MonographStage.DRAFT, MonographStage.REVISION_REQUIRED)
        if self.supervisor_id == user.id:
            return True
        if user.is_head_of_department:
            return self.department_id in user.headed_departments.values_list("id", flat=True)
        return False


class MonographMember(BaseModel):
    """
    A student author on a monograph.

    Modelled as a table rather than a foreign key on Monograph because
    departments may allow two students to write one monograph together. A solo
    monograph is simply a group of one.
    """

    monograph = models.ForeignKey(
        Monograph, on_delete=models.CASCADE, related_name="members"
    )
    student = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="monograph_memberships"
    )
    is_lead = models.BooleanField(
        default=False,
        help_text="The student who submits on behalf of the group.",
    )
    contribution = models.TextField(
        blank=True, help_text="Which part of the work this student is responsible for."
    )

    class Meta:
        ordering = ("-is_lead", "student__full_name")
        constraints = [
            models.UniqueConstraint(
                fields=["monograph", "student"],
                condition=models.Q(is_deleted=False),
                name="unique_student_per_monograph",
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} on {self.monograph.title}"


class StageTransition(BaseModel):
    """
    One move from one stage to another.

    This table is append-only. It is what ends arguments about whether work
    was submitted on time or whether corrections were ever given, so nothing
    in the application ever updates or deletes a row here.
    """

    monograph = models.ForeignKey(
        Monograph, on_delete=models.CASCADE, related_name="transitions"
    )
    from_stage = models.CharField(max_length=32, blank=True)
    to_stage = models.CharField(max_length=32)
    actor = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    note = models.TextField(blank=True)

    # How long the monograph sat in the stage it just left. Stored rather than
    # computed so the "where is the bottleneck" report stays a simple query.
    days_in_previous_stage = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=["monograph", "created_at"])]

    def __str__(self):
        return f"{self.monograph_id}: {self.from_stage} to {self.to_stage}"


class ActivityLog(BaseModel):
    """
    Everything else that happens to a monograph.

    Stage moves live in StageTransition; this records the rest — a file
    uploaded, a supervisor assigned, a comment written, a defense scheduled —
    so one timeline can show the whole story.
    """

    monograph = models.ForeignKey(
        Monograph, on_delete=models.CASCADE, related_name="activities"
    )
    actor = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=64, db_index=True)
    description = models.CharField(max_length=500)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["monograph", "-created_at"])]

    def __str__(self):
        return f"{self.action} on {self.monograph_id}"


class TopicApprovalVote(BaseModel):
    """
    One vote on a proposed topic.

    Only used by departments whose policy is a committee vote; departments
    where the head decides alone record a single vote from the head.
    """

    monograph = models.ForeignKey(
        Monograph, on_delete=models.CASCADE, related_name="topic_votes"
    )
    voter = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="topic_votes"
    )
    approved = models.BooleanField()
    comment = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["monograph", "voter"],
                condition=models.Q(is_deleted=False),
                name="unique_vote_per_voter",
            )
        ]

    def __str__(self):
        verdict = "approved" if self.approved else "rejected"
        return f"{self.voter.full_name} {verdict} {self.monograph_id}"
