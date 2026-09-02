"""Monograph serializers: list, detail, write, and the timeline."""
from rest_framework import serializers

from core.serializers import UserBriefSerializer
from monographs.models import (
    ActivityLog,
    Monograph,
    MonographMember,
    StageTransition,
    TopicApprovalVote,
)


class MonographMemberSerializer(serializers.ModelSerializer):
    student = UserBriefSerializer(read_only=True)
    student_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = MonographMember
        fields = ("id", "student", "student_id", "is_lead", "contribution")


class StageTransitionSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)
    from_stage_label = serializers.SerializerMethodField()
    to_stage_label = serializers.SerializerMethodField()

    class Meta:
        model = StageTransition
        fields = (
            "id",
            "from_stage",
            "from_stage_label",
            "to_stage",
            "to_stage_label",
            "actor",
            "note",
            "days_in_previous_stage",
            "created_at",
        )

    def _label(self, stage):
        from core.enums import MonographStage

        return dict(MonographStage.choices).get(stage, stage)

    def get_from_stage_label(self, obj) -> str:
        return self._label(obj.from_stage) if obj.from_stage else ""

    def get_to_stage_label(self, obj) -> str:
        return self._label(obj.to_stage)


class ActivityLogSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = ("id", "action", "description", "actor", "metadata", "created_at")


class TopicApprovalVoteSerializer(serializers.ModelSerializer):
    voter = UserBriefSerializer(read_only=True)

    class Meta:
        model = TopicApprovalVote
        fields = ("id", "voter", "approved", "comment", "created_at")
        read_only_fields = ("id", "voter", "created_at")


class MonographListSerializer(serializers.ModelSerializer):
    """
    The row shape used in lists and dashboards.

    Everything a card needs to render is here, and nothing more — lists are
    the most-requested endpoint and often loaded over a weak connection.
    """

    stage_label = serializers.CharField(source="get_stage_display", read_only=True)
    progress_percent = serializers.IntegerField(read_only=True)
    days_in_current_stage = serializers.IntegerField(read_only=True)
    supervisor_name = serializers.CharField(source="supervisor.display_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    research_area_name = serializers.CharField(source="research_area.name", read_only=True)
    academic_year_name = serializers.CharField(source="academic_year.name", read_only=True)
    student_names = serializers.ListField(child=serializers.CharField(), read_only=True)
    is_finished = serializers.BooleanField(read_only=True)

    class Meta:
        model = Monograph
        fields = (
            "id",
            "title",
            "stage",
            "stage_label",
            "progress_percent",
            "days_in_current_stage",
            "stage_changed_at",
            "supervisor",
            "supervisor_name",
            "department",
            "department_name",
            "research_area_name",
            "student_names",
            "academic_year",
            "academic_year_name",
            "final_grade",
            "is_finished",
            "created_at",
        )


class MonographDetailSerializer(MonographListSerializer):
    """
    The full record, plus what this particular viewer may do with it.

    ``available_actions`` is what drives the buttons on screen, so a student
    never sees an action the server would refuse.
    """

    members = MonographMemberSerializer(many=True, read_only=True)
    supervisor = UserBriefSerializer(read_only=True)
    available_actions = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta(MonographListSerializer.Meta):
        fields = MonographListSerializer.Meta.fields + (
            "abstract",
            "keywords",
            "objectives",
            "methodology",
            "expected_outcome",
            "closure_reason",
            "completed_at",
            "supervisor_assigned_at",
            "members",
            "available_actions",
            "can_edit",
            "document_count",
            "review_count",
        )

    def get_available_actions(self, obj) -> list[dict]:
        from monographs import workflow

        user = self.context["request"].user
        return [
            {
                "target": t.target,
                "label": t.label,
                "requires_note": t.requires_note,
            }
            for t in workflow.available_transitions(obj, user)
        ]

    def get_can_edit(self, obj) -> bool:
        return obj.is_editable_by(self.context["request"].user)

    def get_document_count(self, obj) -> int:
        return obj.documents.count()

    def get_review_count(self, obj) -> int:
        return obj.reviews.count()


class MonographWriteSerializer(serializers.ModelSerializer):
    """
    Creating and editing the monograph record.

    Members are handled here so a group monograph can be created in one
    request; the stage is never accepted from the client because moving
    between stages is the workflow's job, not a field update.
    """

    member_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = Monograph
        fields = (
            "id",
            "title",
            "abstract",
            "keywords",
            "objectives",
            "methodology",
            "expected_outcome",
            "department",
            "academic_year",
            "research_area",
            "member_ids",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        department = attrs.get("department") or getattr(self.instance, "department", None)
        member_ids = attrs.get("member_ids")

        if member_ids and department:
            policy = getattr(department, "policy", None)
            if policy:
                if len(member_ids) > 1 and not policy.allow_group_monographs:
                    raise serializers.ValidationError(
                        {"member_ids": "This department does not allow group monographs."}
                    )
                if len(member_ids) > policy.max_students_per_monograph:
                    raise serializers.ValidationError(
                        {
                            "member_ids": (
                                f"At most {policy.max_students_per_monograph} students "
                                f"may share one monograph in this department."
                            )
                        }
                    )
        return attrs

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", [])
        request = self.context["request"]
        monograph = Monograph.objects.create(created_by=request.user, **validated_data)

        # A student creating their own monograph is its first author.
        if not member_ids and request.user.is_student:
            member_ids = [request.user.id]

        for index, student_id in enumerate(member_ids):
            MonographMember.objects.create(
                monograph=monograph,
                student_id=student_id,
                is_lead=(index == 0),
                created_by=request.user,
            )
        return monograph

    def update(self, instance, validated_data):
        validated_data.pop("member_ids", None)  # membership changes have their own endpoint
        validated_data["updated_by"] = self.context["request"].user
        return super().update(instance, validated_data)


class TransitionRequestSerializer(serializers.Serializer):
    """Asking to move a monograph to a new stage."""

    target = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class AssignSupervisorSerializer(serializers.Serializer):
    supervisor_id = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True, default="")
