"""Review, comment and discussion serializers."""
from rest_framework import serializers

from core.serializers import UserBriefSerializer
from reviews.models import Discussion, Review, ReviewComment


class ReviewCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewComment
        fields = ("id", "page_number", "section", "body", "is_resolved", "resolved_at")
        read_only_fields = ("id", "resolved_at")


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = UserBriefSerializer(read_only=True)
    decision_label = serializers.CharField(source="get_decision_display", read_only=True)
    items = ReviewCommentSerializer(many=True, read_only=True)
    document_title = serializers.CharField(
        source="document_version.document.title", read_only=True
    )
    document_version_number = serializers.IntegerField(
        source="document_version.version_number", read_only=True
    )

    class Meta:
        model = Review
        fields = (
            "id",
            "monograph",
            "reviewer",
            "decision",
            "decision_label",
            "summary",
            "comments",
            "round_number",
            "score",
            "document_version",
            "document_title",
            "document_version_number",
            "items",
            "created_at",
        )


class ReviewCreateSerializer(serializers.Serializer):
    """
    A supervisor's decision, with its written feedback.

    ``items`` carries corrections pinned to a page or section, so a student
    can work through them one at a time rather than re-reading a wall of text.
    """

    monograph = serializers.UUIDField()
    decision = serializers.CharField()
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    comments = serializers.CharField(required=False, allow_blank=True, default="")
    document_version = serializers.UUIDField(required=False, allow_null=True)
    score = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    move_stage = serializers.BooleanField(default=True)
    items = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate_decision(self, value):
        from core.enums import ReviewDecision

        valid = {choice for choice, _label in ReviewDecision.choices}
        if value not in valid:
            raise serializers.ValidationError(
                f"Unknown decision. Expected one of: {', '.join(sorted(valid))}."
            )
        return value

    def validate_items(self, value):
        for item in value:
            if not item.get("body", "").strip():
                raise serializers.ValidationError("Each correction needs some text.")
        return value


class DiscussionSerializer(serializers.ModelSerializer):
    author = UserBriefSerializer(read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Discussion
        fields = ("id", "monograph", "author", "body", "parent", "reply_count", "created_at")
        read_only_fields = ("id", "author", "created_at")

    def get_reply_count(self, obj) -> int:
        return obj.replies.count()
