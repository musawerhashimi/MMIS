"""
The permanent library of finished monographs.

A completed monograph is copied into an archive entry rather than being read
live from the monograph tables. The archive must stay readable and stable for
years, long after academic years are closed and staff have moved on.
"""
from django.db import models

from core.models import BaseModel


class ArchiveEntry(BaseModel):
    """One finished monograph, as the department's permanent record of it."""

    monograph = models.OneToOneField(
        "monographs.Monograph", on_delete=models.PROTECT, related_name="archive_entry"
    )

    title = models.CharField(max_length=500, db_index=True)
    abstract = models.TextField(blank=True)
    keywords = models.JSONField(default=list, blank=True)

    # Names are copied as text so the entry stays readable even if an account
    # is later deactivated or a department is renamed.
    author_names = models.JSONField(default=list, blank=True)
    supervisor_name = models.CharField(max_length=255, blank=True)
    department_name = models.CharField(max_length=255, blank=True)
    academic_year_name = models.CharField(max_length=64, blank=True)
    research_area_name = models.CharField(max_length=255, blank=True)

    final_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    defended_on = models.DateField(null=True, blank=True)

    #: The approved final file, kept as the copy of record.
    final_document = models.ForeignKey(
        "documents.DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    #: Whether students outside the department may read it.
    is_public = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-defended_on", "title")
        verbose_name_plural = "archive entries"
        indexes = [
            models.Index(fields=["department_name", "academic_year_name"]),
        ]

    def __str__(self):
        return self.title


class TopicSimilarity(BaseModel):
    """
    A flagged resemblance between a proposed topic and an existing one.

    This is a duplicate-topic check within the department's own archive, not
    plagiarism detection against the internet. It exists so two students do
    not unknowingly write the same monograph.
    """

    monograph = models.ForeignKey(
        "monographs.Monograph", on_delete=models.CASCADE, related_name="similarities"
    )
    #: Either an archived monograph or another live one in the same year.
    similar_to = models.ForeignKey(
        "monographs.Monograph", on_delete=models.CASCADE, related_name="flagged_by"
    )
    score = models.PositiveIntegerField(help_text="Percent similarity, 0 to 100.")
    matched_terms = models.JSONField(default=list, blank=True)

    #: The head of department can dismiss a false match so it stops appearing.
    is_dismissed = models.BooleanField(default=False)
    dismissed_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ("-score",)
        verbose_name_plural = "topic similarities"
        constraints = [
            models.UniqueConstraint(
                fields=["monograph", "similar_to"],
                condition=models.Q(is_deleted=False),
                name="unique_similarity_pair",
            )
        ]

    def __str__(self):
        return f"{self.score}% match"
