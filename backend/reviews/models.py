"""
Supervisor decisions and the feedback that goes with them.

A review always points at the exact document version it judged. That is what
lets a supervisor compare an old version against a new one and check whether
the corrections were actually applied, and what settles later disagreements
about whether feedback was ever given.
"""
from django.db import models

from core.enums import ReviewDecision
from core.models import BaseModel


class Review(BaseModel):
    """One decision on one submitted version."""

    monograph = models.ForeignKey(
        "monographs.Monograph", on_delete=models.CASCADE, related_name="reviews"
    )
    document_version = models.ForeignKey(
        "documents.DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviews",
        help_text="The exact file this decision was made about.",
    )

    reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="reviews_given"
    )
    decision = models.CharField(max_length=32, choices=ReviewDecision.choices, db_index=True)

    summary = models.CharField(
        max_length=500, blank=True, help_text="The headline the student sees first."
    )
    comments = models.TextField(
        blank=True, help_text="What must change, in the supervisor's own words."
    )

    #: Which round of revision this is. A proposal corrected three times has
    #: reviews at rounds 1, 2 and 3, and the student can read the whole
    #: sequence.
    round_number = models.PositiveIntegerField(default=1)

    #: Optional mark, used later when the final grade is calculated.
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["monograph", "-created_at"]),
            models.Index(fields=["reviewer", "decision"]),
        ]

    def __str__(self):
        return f"{self.get_decision_display()} by {self.reviewer.full_name}"

    @property
    def requests_changes(self) -> bool:
        return self.decision == ReviewDecision.REVISION_REQUESTED


class ReviewComment(BaseModel):
    """
    A specific correction pinned to one place in the document.

    Separate from the review's general comments so a supervisor can say
    "page 12, this citation is wrong" and the student can tick items off one
    by one.
    """

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="items")

    page_number = models.PositiveIntegerField(null=True, blank=True)
    section = models.CharField(max_length=255, blank=True)
    body = models.TextField()

    #: The student marks each item as done; the supervisor can see what was
    #: addressed without re-reading the whole file.
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("page_number", "created_at")

    def __str__(self):
        where = f"p.{self.page_number}" if self.page_number else self.section or "general"
        return f"{where}: {self.body[:50]}"


class Discussion(BaseModel):
    """
    A message between a student and a supervisor about the monograph.

    Deliberately plain: this replaces the WhatsApp thread where corrections
    used to get lost, so the conversation lives beside the work it is about.
    """

    monograph = models.ForeignKey(
        "monographs.Monograph", on_delete=models.CASCADE, related_name="discussions"
    )
    author = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="discussion_messages"
    )
    body = models.TextField()

    #: Threaded replies, so a long exchange stays readable.
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=["monograph", "created_at"])]

    def __str__(self):
        return f"{self.author.full_name}: {self.body[:50]}"
