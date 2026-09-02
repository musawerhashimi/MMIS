"""Defences: committee, scores and the final grade."""
from django.contrib import admin

from core.admin import BaseModelAdmin
from defenses.models import CommitteeMember, Defense


class CommitteeMemberInline(admin.TabularInline):
    model = CommitteeMember
    extra = 0
    autocomplete_fields = ("member",)
    fields = ("member", "role", "score", "has_read_monograph", "attended", "comments")


@admin.register(Defense)
class DefenseAdmin(BaseModelAdmin):
    list_display = ("monograph", "scheduled_at", "location", "result",
                    "committee_average", "final_grade")
    list_filter = ("result", "scheduled_at")
    search_fields = ("monograph__title", "location")
    date_hierarchy = "scheduled_at"
    inlines = [CommitteeMemberInline]
    readonly_fields = BaseModelAdmin.readonly_fields + ("committee_average", "final_grade")

    fieldsets = (
        ("Schedule", {"fields": ("monograph", "scheduled_at", "duration_minutes", "location")}),
        ("Outcome", {"fields": ("result", "held_at", "supervisor_score",
                                "committee_average", "final_grade", "notes")}),
        ("Revisions", {"fields": ("required_revisions", "revisions_due_date")}),
        ("Record", {"fields": BaseModelAdmin.readonly_fields, "classes": ("collapse",)}),
    )

    @admin.display(description="Committee average")
    def committee_average(self, obj):
        return obj.committee_average or "—"


@admin.register(CommitteeMember)
class CommitteeMemberAdmin(BaseModelAdmin):
    list_display = ("defense", "member", "role", "score", "has_read_monograph", "attended")
    list_filter = ("role", "has_read_monograph", "attended")
    search_fields = ("member__full_name", "defense__monograph__title")
