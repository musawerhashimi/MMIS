"""Archive and similarity serializers."""
from rest_framework import serializers

from archive.models import ArchiveEntry, TopicSimilarity


class ArchiveEntrySerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ArchiveEntry
        fields = (
            "id",
            "monograph",
            "title",
            "abstract",
            "keywords",
            "author_names",
            "supervisor_name",
            "department_name",
            "academic_year_name",
            "research_area_name",
            "final_grade",
            "defended_on",
            "is_public",
            "view_count",
            "download_url",
        )

    def get_download_url(self, obj) -> str | None:
        if obj.final_document_id is None:
            return None
        return f"/api/v1/documents/versions/{obj.final_document_id}/download/"


class TopicSimilaritySerializer(serializers.ModelSerializer):
    similar_title = serializers.CharField(source="similar_to.title", read_only=True)
    similar_year = serializers.CharField(
        source="similar_to.academic_year.name", read_only=True
    )
    similar_students = serializers.ListField(
        source="similar_to.student_names", child=serializers.CharField(), read_only=True
    )

    class Meta:
        model = TopicSimilarity
        fields = (
            "id",
            "monograph",
            "similar_to",
            "similar_title",
            "similar_year",
            "similar_students",
            "score",
            "matched_terms",
            "is_dismissed",
            "dismissed_reason",
            "created_at",
        )
