"""Monograph records and their permanent history."""
from django.contrib import admin
from django.utils.html import format_html

from core.admin import BaseModelAdmin
from monographs.models import (
    ActivityLog, Monograph, MonographMember, StageTransition, TopicApprovalVote,
)


class MonographMemberInline(admin.TabularInline):
    model = MonographMember
    extra = 0
    autocomplete_fields = ("student",)
    fields = ("student", "is_lead", "contribution")


class StageTransitionInline(admin.TabularInline):
    """
    The history, shown read-only.

    This table is the record that settles disagreements, so the admin must
    not be able to rewrite it either.
    """

    model = StageTransition
    extra = 0
    can_delete = False
    fields = ("created_at", "from_stage", "to_stage", "actor", "note", "days_in_previous_stage")
    readonly_fields = fields
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Monograph)
class MonographAdmin(BaseModelAdmin):
    list_display = ("title", "students", "supervisor", "stage_badge", "progress",
                    "department", "academic_year", "final_grade")
    list_filter = ("stage", "department", "academic_year", "research_area")
    search_fields = ("title", "abstract", "members__student__full_name")
    autocomplete_fields = ("supervisor",)
    inlines = [MonographMemberInline, StageTransitionInline]
    readonly_fields = BaseModelAdmin.readonly_fields + ("stage_changed_at", "completed_at")

    fieldsets = (
        ("The work", {"fields": ("title", "abstract", "keywords", "objectives",
                                 "methodology", "expected_outcome")}),
        ("Where it belongs", {"fields": ("department", "academic_year", "research_area")}),
        ("People", {"fields": ("supervisor", "supervisor_assigned_at")}),
        ("Progress", {"fields": ("stage", "stage_changed_at", "closure_reason",
                                 "final_grade", "completed_at")}),
        ("Record", {"fields": BaseModelAdmin.readonly_fields, "classes": ("collapse",)}),
    )

    @admin.display(description="Students")
    def students(self, obj):
        return ", ".join(obj.student_names) or "—"

    @admin.display(description="Stage")
    def stage_badge(self, obj):
        colours = {
            "completed": "#16a34a", "rejected": "#ef4444", "withdrawn": "#64748b",
            "revision_required": "#f97316", "under_review": "#3b82f6",
        }
        colour = colours.get(obj.stage, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px">{}</span>',
            colour, obj.get_stage_display(),
        )

    @admin.display(description="Progress")
    def progress(self, obj):
        return f"{obj.progress_percent}%"


@admin.register(StageTransition)
class StageTransitionAdmin(admin.ModelAdmin):
    """Read-only: the history is never edited, only read."""

    list_display = ("created_at", "monograph", "from_stage", "to_stage", "actor")
    list_filter = ("to_stage", "created_at")
    search_fields = ("monograph__title", "actor__full_name", "note")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "monograph", "action", "description", "actor")
    list_filter = ("action", "created_at")
    search_fields = ("monograph__title", "description")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TopicApprovalVote)
class TopicApprovalVoteAdmin(BaseModelAdmin):
    list_display = ("monograph", "voter", "approved", "created_at")
    list_filter = ("approved",)
