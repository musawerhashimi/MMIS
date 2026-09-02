"""The permanent library, and flagged duplicate topics."""
from django.contrib import admin

from archive.models import ArchiveEntry, TopicSimilarity
from core.admin import BaseModelAdmin


@admin.register(ArchiveEntry)
class ArchiveEntryAdmin(BaseModelAdmin):
    """
    Names and titles here are copies kept as plain text, so an entry stays
    readable years later after accounts are closed and departments renamed.
    """

    list_display = ("title", "authors", "supervisor_name", "academic_year_name",
                    "final_grade", "defended_on", "view_count")
    list_filter = ("academic_year_name", "department_name", "research_area_name", "is_public")
    search_fields = ("title", "abstract", "supervisor_name")
    date_hierarchy = "defended_on"

    @admin.display(description="Authors")
    def authors(self, obj):
        return ", ".join(obj.author_names) or "—"


@admin.register(TopicSimilarity)
class TopicSimilarityAdmin(BaseModelAdmin):
    list_display = ("monograph", "similar_to", "score", "is_dismissed")
    list_filter = ("is_dismissed",)
    search_fields = ("monograph__title", "similar_to__title")
