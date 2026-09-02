"""Serializer building blocks shared across apps."""
from rest_framework import serializers


class TimestampedSerializer(serializers.ModelSerializer):
    """Exposes the audit timestamps every domain model carries."""

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class UserBriefSerializer(serializers.Serializer):
    """
    The small shape of a person, used wherever a name needs to appear next to
    something else — a supervisor on a monograph, an actor in the timeline.

    Kept deliberately thin so listing a hundred monographs does not drag a
    hundred full user records along with it.
    """

    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    avatar = serializers.ImageField(read_only=True)


class ChoiceDisplaySerializer(serializers.Serializer):
    """A stored value paired with its label, so the UI need not map them."""

    value = serializers.CharField()
    label = serializers.CharField()


def choices_payload(choices) -> list[dict]:
    """Turn Django TextChoices into something the frontend can render directly."""
    return [{"value": value, "label": label} for value, label in choices]
