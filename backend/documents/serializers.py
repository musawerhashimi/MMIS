"""Document and version serializers."""
from rest_framework import serializers

from core.serializers import UserBriefSerializer
from documents.models import Document, DocumentVersion


class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by = UserBriefSerializer(read_only=True)
    size_display = serializers.CharField(read_only=True)
    extension = serializers.CharField(read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVersion
        fields = (
            "id",
            "version_number",
            "original_filename",
            "file_size",
            "size_display",
            "extension",
            "content_type",
            "change_note",
            "uploaded_by",
            "download_count",
            "download_url",
            "created_at",
        )

    def get_download_url(self, obj) -> str:
        # Files are never served by URL directly; this points at the checked
        # download view.
        return f"/api/v1/documents/versions/{obj.id}/download/"


class DocumentSerializer(serializers.ModelSerializer):
    document_type_label = serializers.CharField(
        source="get_document_type_display", read_only=True
    )
    current_version = DocumentVersionSerializer(read_only=True)
    version_count = serializers.IntegerField(read_only=True)
    approved_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = Document
        fields = (
            "id",
            "monograph",
            "document_type",
            "document_type_label",
            "title",
            "chapter_number",
            "description",
            "is_approved",
            "approved_at",
            "approved_by",
            "current_version",
            "version_count",
            "created_at",
        )


class DocumentDetailSerializer(DocumentSerializer):
    """Adds the full version history, newest first."""

    versions = DocumentVersionSerializer(many=True, read_only=True)

    class Meta(DocumentSerializer.Meta):
        fields = DocumentSerializer.Meta.fields + ("versions",)


class UploadSerializer(serializers.Serializer):
    """
    An incoming file.

    Multipart rather than JSON, so the file arrives alongside the small amount
    of context needed to file it correctly.
    """

    file = serializers.FileField()
    monograph = serializers.UUIDField()
    document_type = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True, default="")
    chapter_number = serializers.IntegerField(required=False, allow_null=True)
    change_note = serializers.CharField(required=False, allow_blank=True, default="")
    document = serializers.UUIDField(required=False, allow_null=True)

    def validate_document_type(self, value):
        from core.enums import DocumentType

        valid = {choice for choice, _label in DocumentType.choices}
        if value not in valid:
            raise serializers.ValidationError(
                f"Unknown document type. Expected one of: {', '.join(sorted(valid))}."
            )
        return value
