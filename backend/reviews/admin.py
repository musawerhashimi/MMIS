"""Supervisor decisions and the feedback that went with them."""
from django.contrib import admin

from core.admin import BaseModelAdmin
from reviews.models import Discussion, Review, ReviewComment


class ReviewCommentInline(admin.TabularInline):
    model = ReviewComment
    extra = 0
    fields = ("page_number", "section", "body", "is_resolved")


@admin.register(Review)
class ReviewAdmin(BaseModelAdmin):
    """
    Reviews are written once and never edited: a student must be able to
    rely on the feedback they were given.
    """

    list_display = ("monograph", "reviewer", "decision", "round_number", "created_at")
    list_filter = ("decision", "created_at")
    search_fields = ("monograph__title", "reviewer__full_name", "summary", "comments")
    date_hierarchy = "created_at"
    inlines = [ReviewCommentInline]

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReviewComment)
class ReviewCommentAdmin(BaseModelAdmin):
    list_display = ("review", "page_number", "section", "is_resolved")
    list_filter = ("is_resolved",)


@admin.register(Discussion)
class DiscussionAdmin(BaseModelAdmin):
    list_display = ("monograph", "author", "short_body", "created_at")
    search_fields = ("monograph__title", "body")
    date_hierarchy = "created_at"

    @admin.display(description="Message")
    def short_body(self, obj):
        return obj.body[:70] + ("…" if len(obj.body) > 70 else "")
