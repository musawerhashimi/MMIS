"""Defense endpoints: scheduling, scoring and recording the result."""
from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsHeadOfDepartment
from defenses.models import CommitteeMember, Defense
from defenses.serializers import (
    CommitteeMemberSerializer,
    DefenseSerializer,
    RecordResultSerializer,
    ScheduleDefenseSerializer,
    ScoreSerializer,
)
from monographs.models import Monograph
from monographs.services.transitions import log_activity


class DefenseViewSet(viewsets.ModelViewSet):
    """
    Defenses for monographs this person is involved in.

    A committee member sees the defenses they must examine; a head of
    department sees every defense in their department.
    """

    serializer_class = DefenseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["result", "monograph"]
    ordering = ["-scheduled_at"]

    def get_queryset(self):
        visible = Monograph.objects.visible_to(self.request.user)
        return (
            Defense.objects.filter(monograph__in=visible)
            .select_related("monograph")
            .prefetch_related("committee__member")
        )

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "schedule"):
            return [IsHeadOfDepartment()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["post"], permission_classes=[IsHeadOfDepartment])
    @transaction.atomic
    def schedule(self, request):
        """
        Set a date and appoint the committee.

        Re-scheduling an existing defense is allowed and keeps the same
        record, because the monograph's history should show that the date
        moved rather than losing the earlier one.
        """
        from accounts.models import User
        from core.enums import CommitteeRole, NotificationKind
        from notifications.services import notify, notify_many

        serializer = ScheduleDefenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        monograph = Monograph.objects.filter(pk=data["monograph"]).first()
        if monograph is None or not monograph.is_visible_to(request.user):
            return Response(
                {"error": {"code": "not_found", "message": "No such monograph.", "details": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )

        policy = getattr(monograph.department, "policy", None)
        required_size = policy.committee_size if policy else 3
        if len(data["committee"]) < required_size:
            return Response(
                {
                    "error": {
                        "code": "committee_too_small",
                        "message": (
                            f"This department requires {required_size} committee members; "
                            f"{len(data['committee'])} were given."
                        ),
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        defense, created = Defense.objects.get_or_create(
            monograph=monograph, defaults={"created_by": request.user}
        )
        defense.scheduled_at = data["scheduled_at"]
        defense.duration_minutes = data["duration_minutes"]
        defense.location = data["location"]
        defense.updated_by = request.user
        defense.save()

        # Replace the committee wholesale: partial edits have their own
        # endpoint, and this keeps re-scheduling simple to reason about.
        defense.committee.all().delete()
        members = []
        for entry in data["committee"]:
            user = User.objects.filter(pk=entry["member_id"]).first()
            if user is None:
                continue
            members.append(
                CommitteeMember.objects.create(
                    defense=defense,
                    member=user,
                    role=entry.get("role", CommitteeRole.INTERNAL_EXAMINER),
                    created_by=request.user,
                )
            )

        log_activity(
            monograph,
            request.user,
            action="defense_scheduled",
            description=f"Defense set for {defense.scheduled_at:%Y-%m-%d %H:%M} at {defense.location or 'a place to be confirmed'}.",
            defense_id=str(defense.id),
            committee_size=len(members),
        )

        when = f"{defense.scheduled_at:%Y-%m-%d at %H:%M}"
        notify_many(
            [m.student for m in monograph.members.select_related("student")]
            + ([monograph.supervisor] if monograph.supervisor else []),
            kind=NotificationKind.DEFENSE_SCHEDULED,
            title="Defense scheduled",
            body=f"The defense of {monograph.title} is on {when} at {defense.location or 'a place to be confirmed'}.",
            monograph=monograph,
            actor=request.user,
        )
        for seat in members:
            notify(
                seat.member,
                kind=NotificationKind.DEFENSE_SCHEDULED,
                title="You are on a defense committee",
                body=f"{monograph.title} — {when}. Please read the monograph beforehand.",
                monograph=monograph,
                actor=request.user,
            )

        return Response(
            DefenseSerializer(defense).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def score(self, request, pk=None):
        """
        Enter this examiner's mark.

        Each committee member records their own score; nobody can enter a
        score on someone else's behalf.
        """
        defense = self.get_object()
        seat = defense.committee.filter(member=request.user).first()
        if seat is None:
            return Response(
                {
                    "error": {
                        "code": "not_on_committee",
                        "message": "You are not on this defense committee.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ScoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seat.record_score(
            serializer.validated_data["score"], serializer.validated_data.get("comments", "")
        )

        log_activity(
            defense.monograph,
            request.user,
            action="defense_scored",
            description=f"{request.user.display_name} entered a score.",
            defense_id=str(defense.id),
        )
        return Response(
            {
                "committee_member": CommitteeMemberSerializer(seat).data,
                "all_scores_in": defense.all_scores_in,
                "committee_average": defense.committee_average,
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfDepartment])
    def record_result(self, request, pk=None):
        """
        Record the outcome and work out the final grade.

        The grade is calculated from the department's own weights, but the
        result itself is whatever the committee decided — the calculation
        never overrules the people in the room.
        """
        defense = self.get_object()
        serializer = RecordResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not defense.all_scores_in:
            missing = defense.committee.filter(score__isnull=True).count()
            return Response(
                {
                    "error": {
                        "code": "scores_missing",
                        "message": f"{missing} committee member(s) have not entered a score yet.",
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        defense.result = data["result"]
        defense.notes = data.get("notes", "")
        defense.required_revisions = data.get("required_revisions", "")
        defense.revisions_due_date = data.get("revisions_due_date")
        if data.get("supervisor_score") is not None:
            defense.supervisor_score = data["supervisor_score"]
        defense.held_at = timezone.now()
        defense.final_grade = defense.calculate_final_grade()
        defense.updated_by = request.user
        defense.save()

        monograph = defense.monograph
        monograph.final_grade = defense.final_grade
        monograph.save(update_fields=["final_grade", "updated_at"])

        log_activity(
            monograph,
            request.user,
            action="defense_result",
            description=f"Result recorded: {defense.get_result_display()} (grade {defense.final_grade}).",
            defense_id=str(defense.id),
            result=defense.result,
            grade=str(defense.final_grade),
        )
        return Response(DefenseSerializer(defense).data)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """
        An examiner confirms they have read the monograph.

        Lets the head of department see, before the defense day, whether the
        committee is actually prepared.
        """
        defense = self.get_object()
        seat = defense.committee.filter(member=request.user).first()
        if seat is None:
            return Response(
                {
                    "error": {
                        "code": "not_on_committee",
                        "message": "You are not on this defense committee.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        seat.has_read_monograph = True
        seat.save(update_fields=["has_read_monograph"])
        return Response(CommitteeMemberSerializer(seat).data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Defenses still ahead, soonest first."""
        queryset = (
            self.get_queryset()
            .filter(scheduled_at__gte=timezone.now(), result="")
            .order_by("scheduled_at")
        )
        return Response(DefenseSerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def my_committees(self, request):
        """Monographs this person must examine."""
        queryset = (
            Defense.objects.filter(committee__member=request.user)
            .select_related("monograph")
            .prefetch_related("committee__member")
            .distinct()
            .order_by("-scheduled_at")
        )
        return Response(DefenseSerializer(queryset, many=True).data)
