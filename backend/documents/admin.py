"""Uploaded files and their versions."""
from django.contrib import admin

from core.admin import BaseModelAdmin
from documents.models import Document, DocumentVersion, DownloadLog


class DocumentVersionInline(admin.TabularInline):
    """
    Versions are never edited once written — a new upload creates a new row —
    so they are shown read-only here.
    """

    model = DocumentVersion
    extra = 0
    can_delete = False
    fields = ("version_number", "original_filename", "size_display", "uploaded_by",
              "change_note", "created_at")
    readonly_fields = fields
    ordering = ("-version_number",)

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Size")
    def size_display(self, obj):
        return obj.size_display


@admin.register(Document)
class DocumentAdmin(BaseModelAdmin):
    list_display = ("title", "monograph", "document_type", "version_count",
                    "is_approved", "approved_by")
    list_filter = ("document_type", "is_approved")
    search_fields = ("title", "monograph__title")
    inlines = [DocumentVersionInline]

    @admin.display(description="Versions")
    def version_count(self, obj):
        return obj.version_count


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version_number", "original_filename", "size_display",
                    "uploaded_by", "download_count", "created_at")
    search_fields = ("original_filename", "document__title")
    readonly_fields = ("checksum", "file_size", "download_count")

    @admin.display(description="Size")
    def size_display(self, obj):
        return obj.size_display


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    """Who opened which file. Read-only, kept as evidence."""

    list_display = ("created_at", "user", "version", "ip_address")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
