"""Monograph endpoints: the list, the record, and the actions on it."""
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.enums import FINISHED_STAGES, MonographStage
from core.pagination import SmallPagination
from core.permissions import CanEditMonograph, IsHeadOfDepartment
from monographs.filters import MonographFilter
from monographs.models import Monograph
from monographs.serializers import (
    ActivityLogSerializer,
    AssignSupervisorSerializer,
    MonographDetailSerializer,
    MonographListSerializer,
    MonographWriteSerializer,
    StageTransitionSerializer,
    TopicApprovalVoteSerializer,
    TransitionRequestSerializer,
)
from monographs.services.transitions import log_activity, perform_transition


class MonographViewSet(viewsets.ModelViewSet):
    """
    Monographs, scoped to what the signed-in person is allowed to see.

    The queryset is filtered by relationship rather than by role alone: a
    supervisor sees their own students, a head of department sees their
    department, a student sees only their own work.
    """

    permission_classes = [IsAuthenticated, CanEditMonograph]
    #: Actions whose own rules decide access. The workflow already knows who
    #: may move a monograph and when, so applying the record-editing rule on
    #: top of it would refuse legitimate moves — a student may submit a
    #: proposal at a stage where they may no longer edit the record itself.
    workflow_actions = {
        "transition",
        "assign_supervisor",
        "vote_topic",
        "timeline",
        "history",
    }
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MonographFilter
    search_fields = ["title", "abstract", "keywords"]
    ordering_fields = ["created_at", "stage_changed_at", "title", "final_grade"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Monograph.objects.visible_to(self.request.user)
            .select_related("supervisor", "department", "academic_year", "research_area")
            .prefetch_related("members__student")
        )

    def get_permissions(self):
        if self.action in self.workflow_actions:
            from core.permissions import IsMonographParticipant

            # Respect any permissions the action declared for itself
            # (assign_supervisor requires a head of department), and add the
            # visibility check every workflow action needs.
            handler = getattr(self, self.action, None)
            declared = getattr(handler, "kwargs", {}).get("permission_classes")
            if declared:
                return [IsAuthenticated(), IsMonographParticipant()] + [
                    permission() for permission in declared
                ]
            return [IsAuthenticated(), IsMonographParticipant()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MonographWriteSerializer
        if self.action == "list":
            return MonographListSerializer
        return MonographDetailSerializer

    # -- Actions on one monograph -----------------------------------------

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        """
        Move this monograph to a new stage.

        Every stage change in the system arrives here, so the rules and the
        history are applied the same way no matter which screen asked.
        """
        monograph = self.get_object()
        serializer = TransitionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = perform_transition(
            monograph=monograph,
            user=request.user,
            target=serializer.validated_data["target"],
            note=serializer.validated_data.get("note", ""),
        )
        monograph.refresh_from_db()
        return Response(
            {
                "transition": StageTransitionSerializer(record).data,
                "monograph": MonographDetailSerializer(
                    monograph, context={"request": request}
                ).data,
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfDepartment])
    def assign_supervisor(self, request, pk=None):
        """
        Give this monograph a supervisor.

        Capacity is checked but not enforced as a hard block: a head of
        department sometimes has to overload someone deliberately, and the
        dashboard will show it.
        """
        from accounts.models import User
        from notifications.services import notify_supervisor_assigned

        monograph = self.get_object()
        serializer = AssignSupervisorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        supervisor = User.objects.filter(
            id=serializer.validated_data["supervisor_id"]
        ).first()
        if supervisor is None or not supervisor.can_supervise:
            return Response(
                {
                    "error": {
                        "code": "invalid_supervisor",
                        "message": "That person cannot supervise monographs.",
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous = monograph.supervisor
        monograph.supervisor = supervisor
        monograph.updated_by = request.user
        monograph.save(update_fields=["supervisor", "updated_by", "updated_at"])

        log_activity(
            monograph,
            request.user,
            action="supervisor_assigned",
            description=f"{supervisor.display_name} assigned as supervisor.",
            supervisor_id=str(supervisor.id),
            previous_supervisor=previous.display_name if previous else None,
        )
        notify_supervisor_assigned(monograph, supervisor, request.user)

        profile = getattr(supervisor, "supervisor_profile", None)
        return Response(
            {
                "detail": f"{supervisor.display_name} is now supervising this monograph.",
                "supervisor_load": {
                    "active_students": profile.active_student_count if profile else None,
                    "max_students": profile.effective_max_students if profile else None,
                    "over_capacity": (not profile.has_capacity) if profile else False,
                },
            }
        )

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        """
        The full story of this monograph.

        Stage moves and other activity are merged into one list, because the
        person reading it wants the sequence of events, not two tables.
        """
        monograph = self.get_object()

        transitions = [
            {**StageTransitionSerializer(t).data, "type": "transition"}
            for t in monograph.transitions.select_related("actor")
        ]
        activities = [
            {**ActivityLogSerializer(a).data, "type": "activity"}
            for a in monograph.activities.select_related("actor")
            if a.action != "stage_changed"  # already covered by the transition row
        ]

        merged = sorted(
            transitions + activities, key=lambda item: item["created_at"], reverse=True
        )
        return Response(merged)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Stage moves only — the formal record, in the order they happened."""
        monograph = self.get_object()
        return Response(
            StageTransitionSerializer(
                monograph.transitions.select_related("actor"), many=True
            ).data
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def vote_topic(self, request, pk=None):
        """
        Record a vote on a proposed topic.

        Used by departments whose policy is a committee decision rather than
        the head deciding alone.
        """
        from monographs.models import TopicApprovalVote

        monograph = self.get_object()
        if not (request.user.can_supervise or request.user.is_admin):
            return Response(
                {
                    "error": {
                        "code": "not_allowed",
                        "message": "Only teaching staff may vote on topics.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        approved = bool(request.data.get("approved"))
        vote, _created = TopicApprovalVote.objects.update_or_create(
            monograph=monograph,
            voter=request.user,
            defaults={
                "approved": approved,
                "comment": request.data.get("comment", ""),
                "created_by": request.user,
            },
        )
        log_activity(
            monograph,
            request.user,
            action="topic_vote",
            description=f"Voted to {'approve' if approved else 'reject'} the topic.",
        )
        return Response(TopicApprovalVoteSerializer(vote).data)

    # -- Views over many monographs ---------------------------------------

    @action(detail=False, methods=["get"])
    def mine(self, request):
        """The signed-in person's own work, whichever side of it they are on."""
        queryset = self.filter_queryset(self.get_queryset())
        if request.user.is_student:
            queryset = queryset.filter(members__student=request.user)
        elif request.user.can_supervise:
            queryset = queryset.filter(supervisor=request.user)

        page = self.paginate_queryset(queryset)
        serializer = MonographListSerializer(
            page if page is not None else queryset, many=True, context={"request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], pagination_class=SmallPagination)
    def awaiting_me(self, request):
        """
        Work that is waiting on this person right now.

        This is the supervisor's first screen: the point is to answer "what do
        I have to do today" without reading a full list.
        """
        queryset = self.get_queryset().awaiting_supervisor()
        if request.user.can_supervise and not request.user.is_admin:
            queryset = queryset.filter(supervisor=request.user)

        queryset = queryset.order_by("stage_changed_at")  # longest waiting first
        page = self.paginate_queryset(queryset)
        serializer = MonographListSerializer(
            page if page is not None else queryset, many=True, context={"request": request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stage_summary(self, request):
        """
        How many monographs sit at each stage.

        Feeds the donut and the stage columns on the dashboard, so it returns
        every stage including the empty ones — a gap in the chart is
        information too.
        """
        queryset = self.filter_queryset(self.get_queryset())
        counts = dict(
            queryset.values_list("stage").annotate(total=Count("id")).values_list(
                "stage", "total"
            )
        )
        return Response(
            [
                {
                    "stage": stage,
                    "label": label,
                    "count": counts.get(stage, 0),
                    "is_finished": stage in FINISHED_STAGES,
                }
                for stage, label in MonographStage.choices
            ]
        )
