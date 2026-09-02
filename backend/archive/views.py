"""The permanent library, and the duplicate-topic check."""
from django.db.models import F
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from archive.models import ArchiveEntry, TopicSimilarity
from archive.serializers import ArchiveEntrySerializer, TopicSimilaritySerializer
from archive.services.similarity import find_similar, record_similarities
from core.pagination import LargePagination
from core.permissions import IsHeadOfDepartment
from monographs.models import Monograph


class ArchiveViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Finished monographs, searchable.

    This is the thing that did not exist before: past work future students can
    read instead of starting from nothing every year.
    """

    serializer_class = ArchiveEntrySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LargePagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["department_name", "academic_year_name", "research_area_name"]
    search_fields = ["title", "abstract", "keywords", "author_names", "supervisor_name"]
    ordering_fields = ["defended_on", "title", "final_grade"]
    ordering = ["-defended_on"]

    def get_queryset(self):
        queryset = ArchiveEntry.objects.select_related("final_document")
        user = self.request.user
        # Anyone not signed in — including the schema generator — sees only
        # what the department has chosen to publish.
        if not (user.is_authenticated and user.is_admin):
            queryset = queryset.filter(is_public=True)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        entry = self.get_object()
        # Counted with an update rather than a save so concurrent readers do
        # not overwrite each other's increments.
        ArchiveEntry.objects.filter(pk=entry.pk).update(view_count=F("view_count") + 1)
        return Response(ArchiveEntrySerializer(entry).data)

    @action(detail=False, methods=["get"])
    def years(self, request):
        """Which years the archive covers, for the browse filter."""
        rows = (
            self.get_queryset()
            .values("academic_year_name")
            .distinct()
            .order_by("-academic_year_name")
        )
        return Response([row["academic_year_name"] for row in rows if row["academic_year_name"]])

    @action(detail=False, methods=["get"])
    def areas(self, request):
        rows = (
            self.get_queryset()
            .values("research_area_name")
            .distinct()
            .order_by("research_area_name")
        )
        return Response([row["research_area_name"] for row in rows if row["research_area_name"]])


class SimilarityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Possible duplicate topics.

    Shown to the head of department at the moment they are deciding whether to
    approve a topic, which is the only moment it is useful.
    """

    serializer_class = TopicSimilaritySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["monograph", "is_dismissed"]
    ordering = ["-score"]

    def get_queryset(self):
        visible = Monograph.objects.visible_to(self.request.user)
        return TopicSimilarity.objects.filter(monograph__in=visible).select_related(
            "similar_to__academic_year"
        )

    @action(detail=False, methods=["post"])
    def check(self, request):
        """
        Compare a topic against the department's existing work.

        Runs on demand rather than on every save, because it reads every
        monograph in the department and a student editing a draft title should
        not trigger that each keystroke.
        """
        monograph_id = request.data.get("monograph")
        monograph = Monograph.objects.filter(pk=monograph_id).first()
        if monograph is None or not monograph.is_visible_to(request.user):
            return Response(
                {"error": {"code": "not_found", "message": "No such monograph.", "details": {}}},
                status=404,
            )

        matches = find_similar(monograph)
        record_similarities(monograph)
        return Response(
            {
                "monograph": str(monograph.id),
                "match_count": len(matches),
                "matches": matches,
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfDepartment])
    def dismiss(self, request, pk=None):
        """
        Mark a flagged match as a false alarm.

        Two monographs can share vocabulary without being the same work, and
        once a head of department has judged that, it should stop reappearing.
        """
        similarity = self.get_object()
        similarity.is_dismissed = True
        similarity.dismissed_reason = request.data.get("reason", "")
        similarity.save(update_fields=["is_dismissed", "dismissed_reason"])
        return Response(TopicSimilaritySerializer(similarity).data)
