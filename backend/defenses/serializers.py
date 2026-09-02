"""Defense, committee and scoring serializers."""
from rest_framework import serializers

from core.serializers import UserBriefSerializer
from defenses.models import CommitteeMember, Defense


class CommitteeMemberSerializer(serializers.ModelSerializer):
    member = UserBriefSerializer(read_only=True)
    member_id = serializers.UUIDField(write_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = CommitteeMember
        fields = (
            "id",
            "member",
            "member_id",
            "role",
            "role_label",
            "score",
            "comments",
            "scored_at",
            "has_read_monograph",
            "attended",
        )
        read_only_fields = ("id", "scored_at")


class DefenseSerializer(serializers.ModelSerializer):
    committee = CommitteeMemberSerializer(many=True, read_only=True)
    committee_average = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    all_scores_in = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    result_label = serializers.CharField(source="get_result_display", read_only=True)
    monograph_title = serializers.CharField(source="monograph.title", read_only=True)
    student_names = serializers.ListField(
        source="monograph.student_names", child=serializers.CharField(), read_only=True
    )

    class Meta:
        model = Defense
        fields = (
            "id",
            "monograph",
            "monograph_title",
            "student_names",
            "scheduled_at",
            "duration_minutes",
            "location",
            "result",
            "result_label",
            "held_at",
            "supervisor_score",
            "committee_average",
            "final_grade",
            "all_scores_in",
            "is_upcoming",
            "notes",
            "required_revisions",
            "revisions_due_date",
            "committee",
        )
        read_only_fields = ("id", "held_at", "final_grade")


class ScheduleDefenseSerializer(serializers.Serializer):
    """
    Setting the date and forming the committee in one step.

    They belong together: a defense with a date but no examiners is not
    actually scheduled, and the workflow will refuse to move on it.
    """

    monograph = serializers.UUIDField()
    scheduled_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(default=60)
    location = serializers.CharField(allow_blank=True, default="")
    committee = serializers.ListField(child=serializers.DictField())

    def validate_committee(self, value):
        from core.enums import CommitteeRole

        if not value:
            raise serializers.ValidationError("A defense needs a committee.")

        valid_roles = {choice for choice, _label in CommitteeRole.choices}
        seen = set()
        for entry in value:
            member_id = entry.get("member_id")
            if not member_id:
                raise serializers.ValidationError("Each committee entry needs a member_id.")
            if member_id in seen:
                raise serializers.ValidationError(
                    "The same person cannot sit on a committee twice."
                )
            seen.add(member_id)

            role = entry.get("role", CommitteeRole.INTERNAL_EXAMINER)
            if role not in valid_roles:
                raise serializers.ValidationError(
                    f"Unknown committee role '{role}'."
                )
        return value


class ScoreSerializer(serializers.Serializer):
    """One examiner's mark and remarks."""

    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("A score must be between 0 and 100.")
        return value


class RecordResultSerializer(serializers.Serializer):
    """The outcome of the defense, once it has been held."""

    result = serializers.CharField()
    supervisor_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    required_revisions = serializers.CharField(required=False, allow_blank=True, default="")
    revisions_due_date = serializers.DateField(required=False, allow_null=True)

    def validate_result(self, value):
        from core.enums import DefenseResult

        valid = {choice for choice, _label in DefenseResult.choices}
        if value not in valid:
            raise serializers.ValidationError(
                f"Unknown result. Expected one of: {', '.join(sorted(valid))}."
            )
        return value
