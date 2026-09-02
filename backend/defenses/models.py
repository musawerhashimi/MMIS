"""
The defense: committee, schedule, scores and the final grade.

Grade calculation reads its weights from the department policy rather than
hard-coding them, because how much comes from the supervisor and how much
from the committee differs between departments.
"""
from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.enums import CommitteeRole, DefenseResult
from core.models import BaseModel


class Defense(BaseModel):
    """One scheduled defense for one monograph."""

    monograph = models.OneToOneField(
        "monographs.Monograph", on_delete=models.CASCADE, related_name="defense"
    )

    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    location = models.CharField(max_length=255, blank=True)

    result = models.CharField(
        max_length=32, choices=DefenseResult.choices, blank=True, db_index=True
    )
    held_at = models.DateTimeField(null=True, blank=True)

    #: The supervisor's own mark, weighed against the committee average.
    supervisor_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    final_grade = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    notes = models.TextField(blank=True)

    #: Corrections the committee required before the archive copy is accepted.
    required_revisions = models.TextField(blank=True)
    revisions_due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ("-scheduled_at",)

    def __str__(self):
        return f"Defense of {self.monograph.title}"

    @property
    def is_scheduled(self) -> bool:
        return self.scheduled_at is not None

    @property
    def is_upcoming(self) -> bool:
        return bool(self.scheduled_at and self.scheduled_at > timezone.now() and not self.result)

    @property
    def committee_average(self) -> Decimal | None:
        """Mean of the scores the committee actually entered."""
        scores = [m.score for m in self.committee.all() if m.score is not None]
        if not scores:
            return None
        return (sum(scores) / Decimal(len(scores))).quantize(Decimal("0.01"))

    @property
    def all_scores_in(self) -> bool:
        return self.committee.exists() and not self.committee.filter(score__isnull=True).exists()

    def calculate_final_grade(self) -> Decimal | None:
        """
        Combine the supervisor's mark and the committee average.

        Falls back to whichever part exists: a department that does not use a
        supervisor mark still gets a grade from the committee alone.
        """
        committee = self.committee_average
        policy = getattr(self.monograph.department, "policy", None)

        if policy is None:
            return committee

        supervisor = self.supervisor_score

        if supervisor is None and committee is None:
            return None
        if supervisor is None:
            return committee
        if committee is None:
            return supervisor

        weighted = (
            supervisor * Decimal(policy.supervisor_grade_weight)
            + committee * Decimal(policy.committee_grade_weight)
        ) / Decimal(100)
        return weighted.quantize(Decimal("0.01"))

    def derive_result(self) -> str | None:
        """
        What the grade implies, as a starting point for the head of department.

        Only ever a suggestion — the committee's own decision is what gets
        recorded, so this never overwrites a result that was set by a person.
        """
        grade = self.final_grade or self.calculate_final_grade()
        if grade is None:
            return None
        policy = getattr(self.monograph.department, "policy", None)
        passing = policy.passing_grade if policy else Decimal(60)
        return DefenseResult.PASSED if grade >= passing else DefenseResult.FAILED


class CommitteeMember(BaseModel):
    """
    One person on a defense committee, and the score they gave.

    Committee membership is recorded here per defense rather than as a role on
    the user, because the same professor sits on many committees and
    supervises elsewhere.
    """

    defense = models.ForeignKey(
        Defense, on_delete=models.CASCADE, related_name="committee"
    )
    member = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="committee_seats"
    )
    role = models.CharField(
        max_length=32, choices=CommitteeRole.choices, default=CommitteeRole.INTERNAL_EXAMINER
    )

    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comments = models.TextField(blank=True)
    scored_at = models.DateTimeField(null=True, blank=True)

    #: Whether this examiner has opened the monograph before the defense day.
    has_read_monograph = models.BooleanField(default=False)
    attended = models.BooleanField(default=True)

    class Meta:
        ordering = ("role", "member__full_name")
        constraints = [
            models.UniqueConstraint(
                fields=["defense", "member"],
                condition=models.Q(is_deleted=False),
                name="unique_member_per_defense",
            )
        ]

    def __str__(self):
        return f"{self.member.display_name} ({self.get_role_display()})"

    def record_score(self, score, comments=""):
        self.score = score
        self.comments = comments
        self.scored_at = timezone.now()
        self.save(update_fields=["score", "comments", "scored_at", "updated_at"])
