"""Department structure and configuration endpoints."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.enums import (
    CommitteeRole,
    DefenseResult,
    DocumentType,
    MonographStage,
    ReviewDecision,
    Role,
    SupervisorAssignmentMode,
    TopicApprovalMode,
)
from core.permissions import IsAdmin, IsHeadOfDepartment, ReadOnly
from core.serializers import choices_payload
from organization.models import (
    AcademicYear,
    Department,
    DepartmentPolicy,
    Faculty,
    ResearchArea,
    StageDeadline,
)
from organization.serializers import (
    AcademicYearSerializer,
    DepartmentPolicySerializer,
    DepartmentSerializer,
    FacultySerializer,
    ResearchAreaSerializer,
    StageDeadlineSerializer,
)


def action_permissions(view, fallback):
    """
    Permissions for the current request.

    Custom actions declare their own rules; only the plain CRUD verbs fall
    back to the viewset-wide rule. Without this, a method-based check would
    quietly override what an @action asked for.
    """
    handler = getattr(view, view.action, None) if view.action else None
    declared = getattr(handler, "kwargs", {}).get("permission_classes")
    if declared:
        return [permission() for permission in declared]
    return fallback


class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    search_fields = ["name", "code"]

    def get_permissions(self):
        return action_permissions(
            self,
            [IsAuthenticated()] if self.request.method == "GET" else [IsAdmin()],
        )


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("faculty", "head", "policy")
    serializer_class = DepartmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["faculty"]
    search_fields = ["name", "code"]

    def get_permissions(self):
        return action_permissions(
            self,
            [IsAuthenticated()] if self.request.method == "GET" else [IsAdmin()],
        )

    @action(detail=True, methods=["get", "patch"], permission_classes=[IsHeadOfDepartment])
    def policy(self, request, pk=None):
        """
        Read or change how this department runs its process.

        Kept on the department rather than as a standalone resource because a
        policy has no meaning apart from the department it belongs to.
        """
        department = self.get_object()
        policy, _ = DepartmentPolicy.objects.get_or_create(department=department)

        if request.method == "GET":
            return Response(DepartmentPolicySerializer(policy).data)

        serializer = DepartmentPolicySerializer(policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["is_current", "is_closed"]

    def get_permissions(self):
        return action_permissions(
            self,
            [IsAuthenticated()] if self.request.method == "GET" else [IsAdmin()],
        )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def current(self, request):
        """The year new work belongs to. Dashboards default to it."""
        year = AcademicYear.current()
        if year is None:
            return Response(None)
        return Response(AcademicYearSerializer(year).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def set_current(self, request, pk=None):
        year = self.get_object()
        year.is_current = True
        year.save()
        return Response(AcademicYearSerializer(year).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def close(self, request, pk=None):
        """
        Freeze a finished year.

        A closed year stops accepting submissions but stays fully readable, so
        last year's monographs remain available in the archive.
        """
        year = self.get_object()
        year.is_closed = True
        year.save(update_fields=["is_closed"])
        return Response(AcademicYearSerializer(year).data)


class ResearchAreaViewSet(viewsets.ModelViewSet):
    queryset = ResearchArea.objects.select_related("department")
    serializer_class = ResearchAreaSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["department"]
    search_fields = ["name"]

    def get_permissions(self):
        return action_permissions(
            self,
            [IsAuthenticated()] if self.request.method == "GET" else [IsHeadOfDepartment()],
        )


class StageDeadlineViewSet(viewsets.ModelViewSet):
    queryset = StageDeadline.objects.select_related("department", "academic_year")
    serializer_class = StageDeadlineSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["department", "academic_year", "stage"]

    def get_permissions(self):
        return action_permissions(
            self,
            [IsAuthenticated()] if self.request.method == "GET" else [IsHeadOfDepartment()],
        )


class ChoicesView(viewsets.ViewSet):
    """
    Every dropdown the frontend needs, from one request.

    Serving these from the backend keeps the labels in one place, so a stage
    renamed here is renamed everywhere without touching the frontend.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(
            {
                "roles": choices_payload(Role.choices),
                "stages": choices_payload(MonographStage.choices),
                "document_types": choices_payload(DocumentType.choices),
                "review_decisions": choices_payload(ReviewDecision.choices),
                "defense_results": choices_payload(DefenseResult.choices),
                "committee_roles": choices_payload(CommitteeRole.choices),
                "topic_approval_modes": choices_payload(TopicApprovalMode.choices),
                "supervisor_assignment_modes": choices_payload(
                    SupervisorAssignmentMode.choices
                ),
            }
        )
