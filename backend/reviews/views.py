"""Review and discussion endpoints."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.models import DocumentVersion
from monographs.models import Monograph
from monographs.serializers import MonographDetailSerializer
from reviews.models import Discussion, Review, ReviewComment
from reviews.serializers import (
    DiscussionSerializer,
    ReviewCommentSerializer,
    ReviewCreateSerializer,
    ReviewSerializer,
)
from reviews.services.submit import submit_review


class ReviewViewSet(viewsets.ModelViewSet):
    """
    Supervisor decisions.

    Reviews are never edited or deleted once written: a student must be able
    to rely on the feedback they were given, and the record is what settles
    later disagreements.
    """

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["monograph", "decision", "reviewer"]
    http_method_names = ["get", "post", "head", "options"]
    ordering = ["-created_at"]

    def get_queryset(self):
        visible = Monograph.objects.visible_to(self.request.user)
        return (
            Review.objects.filter(monograph__in=visible)
            .select_related("reviewer", "document_version__document")
            .prefetch_related("items")
        )

    def create(self, request, *args, **kwargs):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        monograph = Monograph.objects.filter(pk=data["monograph"]).first()
        if monograph is None or not monograph.is_visible_to(request.user):
            return Response(
                {"error": {"code": "not_found", "message": "No such monograph.", "details": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )

        version = None
        if data.get("document_version"):
            version = DocumentVersion.objects.filter(
                pk=data["document_version"], document__monograph=monograph
            ).first()

        review, transition = submit_review(
            monograph=monograph,
            reviewer=request.user,
            decision=data["decision"],
            summary=data.get("summary", ""),
            comments=data.get("comments", ""),
            document_version=version,
            score=data.get("score"),
            items=data.get("items"),
            move_stage=data.get("move_stage", True),
        )

        monograph.refresh_from_db()
        return Response(
            {
                "review": ReviewSerializer(review).data,
                "moved_to": transition.to_stage if transition else None,
                "monograph": MonographDetailSerializer(
                    monograph, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def for_monograph(self, request):
        """
        Every review on one monograph, oldest first.

        This is the student's feedback screen: read in order, it shows what
        was asked for and what changed between rounds.
        """
        monograph_id = request.query_params.get("monograph")
        if not monograph_id:
            return Response(
                {
                    "error": {
                        "code": "validation",
                        "message": "A monograph id is required.",
                        "details": {"monograph": "This query parameter is required."},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.get_queryset().filter(monograph_id=monograph_id).order_by("created_at")
        return Response(ReviewSerializer(queryset, many=True).data)


class ReviewCommentViewSet(viewsets.ModelViewSet):
    """
    Individual corrections.

    Students may only mark them resolved; the text itself belongs to the
    supervisor who wrote it.
    """

    serializer_class = ReviewCommentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        visible = Monograph.objects.visible_to(self.request.user)
        return ReviewComment.objects.filter(review__monograph__in=visible)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Mark one correction as done."""
        from django.utils import timezone

        item = self.get_object()
        item.is_resolved = True
        item.resolved_at = timezone.now()
        item.save(update_fields=["is_resolved", "resolved_at"])
        return Response(ReviewCommentSerializer(item).data)

    @action(detail=True, methods=["post"])
    def unresolve(self, request, pk=None):
        item = self.get_object()
        item.is_resolved = False
        item.resolved_at = None
        item.save(update_fields=["is_resolved", "resolved_at"])
        return Response(ReviewCommentSerializer(item).data)


class DiscussionViewSet(viewsets.ModelViewSet):
    """
    Messages between a student and their supervisor.

    This is what replaces the scattered phone calls and WhatsApp messages, so
    the conversation stays attached to the work it concerns.
    """

    serializer_class = DiscussionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["monograph", "parent"]
    ordering = ["created_at"]

    def get_queryset(self):
        visible = Monograph.objects.visible_to(self.request.user)
        return (
            Discussion.objects.filter(monograph__in=visible)
            .select_related("author")
            .prefetch_related("replies")
        )

    def perform_create(self, serializer):
        from monographs.services.transitions import log_activity

        discussion = serializer.save(author=self.request.user, created_by=self.request.user)
        log_activity(
            discussion.monograph,
            self.request.user,
            action="message_posted",
            description=f"{self.request.user.full_name} posted a message.",
        )
