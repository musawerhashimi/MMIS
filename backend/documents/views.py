"""Document endpoints: upload, list, approve, and controlled download."""
from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import DomainError
from documents.models import Document, DocumentVersion, DownloadLog
from documents.serializers import (
    DocumentDetailSerializer,
    DocumentSerializer,
    DocumentVersionSerializer,
    UploadSerializer,
)
from documents.services.uploads import can_access_document, can_upload_to, upload_version
from monographs.models import Monograph


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Documents on monographs this person may see.

    Read-only because documents are created by uploading a file, not by
    posting a record — see UploadView.
    """

    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["monograph", "document_type", "is_approved"]
    ordering = ["document_type", "chapter_number"]

    def get_queryset(self):
        visible = Monograph.objects.visible_to(self.request.user)
        return (
            Document.objects.filter(monograph__in=visible)
            .select_related("monograph", "approved_by")
            .prefetch_related("versions__uploaded_by")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DocumentDetailSerializer
        return DocumentSerializer

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Mark this document as accepted.

        Separate from approving the monograph's stage: a supervisor often
        signs off chapter 2 while the work as a whole is still in progress.
        """
        from django.utils import timezone

        from documents.realtime import broadcast_document_approved
        from monographs.services.transitions import log_activity

        document = self.get_object()
        monograph = document.monograph

        if not (
            request.user.is_admin
            or monograph.supervisor_id == request.user.id
            or request.user.is_head_of_department
        ):
            return Response(
                {
                    "error": {
                        "code": "not_allowed",
                        "message": "Only the supervisor or head of department can approve a document.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        document.is_approved = True
        document.approved_at = timezone.now()
        document.approved_by = request.user
        document.save(update_fields=["is_approved", "approved_at", "approved_by"])

        log_activity(
            monograph,
            request.user,
            action="document_approved",
            description=f"{document.title} approved.",
            document_id=str(document.id),
        )
        broadcast_document_approved(monograph, document, request.user)
        return Response(DocumentSerializer(document).data)

    @action(detail=True, methods=["get"])
    def compare(self, request, pk=None):
        """
        Two versions side by side.

        This is how a supervisor checks whether the corrections they asked for
        were actually applied, so it returns both files' details together with
        what the student said had changed.
        """
        document = self.get_object()
        versions = list(document.versions.order_by("-version_number"))

        if len(versions) < 2:
            return Response(
                {
                    "error": {
                        "code": "not_enough_versions",
                        "message": "This document has only one version, so there is nothing to compare.",
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        requested_from = request.query_params.get("from")
        requested_to = request.query_params.get("to")

        def pick(number, fallback):
            if number is None:
                return fallback
            found = next((v for v in versions if str(v.version_number) == str(number)), None)
            if found is None:
                raise Http404(f"This document has no version {number}.")
            return found

        newer = pick(requested_to, versions[0])
        older = pick(requested_from, versions[1])

        return Response(
            {
                "document": DocumentSerializer(document).data,
                "older": DocumentVersionSerializer(older).data,
                "newer": DocumentVersionSerializer(newer).data,
                "same_file": bool(older.checksum) and older.checksum == newer.checksum,
                "reviews_between": _reviews_between(document, older, newer),
            }
        )


def _reviews_between(document, older, newer) -> list[dict]:
    """
    The feedback that prompted the newer version.

    Showing it alongside the comparison saves the supervisor from opening a
    second screen to remember what they had asked for.
    """
    from reviews.models import Review

    reviews = Review.objects.filter(
        document_version__document=document,
        created_at__gte=older.created_at,
        created_at__lte=newer.created_at,
    ).select_related("reviewer")

    return [
        {
            "id": str(r.id),
            "decision": r.decision,
            "summary": r.summary,
            "comments": r.comments,
            "reviewer": r.reviewer.full_name,
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


class UploadView(APIView):
    """Receive a file and store it as the next version of a document."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = UploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        monograph = Monograph.objects.filter(pk=data["monograph"]).first()
        if monograph is None or not monograph.is_visible_to(request.user):
            raise Http404("No such monograph.")

        if not can_upload_to(monograph, request.user):
            return Response(
                {
                    "error": {
                        "code": "not_allowed",
                        "message": "You cannot add files to this monograph.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        document = None
        if data.get("document"):
            document = Document.objects.filter(
                pk=data["document"], monograph=monograph
            ).first()
            if document is None:
                raise Http404("No such document on this monograph.")

        try:
            version = upload_version(
                monograph=monograph,
                user=request.user,
                uploaded_file=data["file"],
                document_type=data["document_type"],
                title=data.get("title", ""),
                chapter_number=data.get("chapter_number"),
                change_note=data.get("change_note", ""),
                document=document,
            )
        except DomainError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface validation cleanly
            return Response(
                {
                    "error": {
                        "code": "upload_failed",
                        "message": str(exc),
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "version": DocumentVersionSerializer(version).data,
                "document": DocumentSerializer(version.document).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DownloadView(APIView):
    """
    Serve one file, to one person who is allowed to read it.

    Every download passes through here rather than being served straight off
    disk, because a monograph draft is private to the people working on it.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, version_id):
        version = (
            DocumentVersion.objects.filter(pk=version_id)
            .select_related("document__monograph")
            .first()
        )
        if version is None:
            raise Http404("No such file.")

        if not can_access_document(version.document, request.user):
            # Deliberately the same answer as a missing file: a person who
            # cannot read it should not learn that it exists.
            raise Http404("No such file.")

        DownloadLog.objects.create(
            version=version,
            user=request.user,
            ip_address=_client_ip(request),
            created_by=request.user,
        )
        DocumentVersion.objects.filter(pk=version.pk).update(
            download_count=version.download_count + 1
        )

        response = FileResponse(
            version.file.open("rb"),
            as_attachment=True,
            filename=version.original_filename,
        )
        return response


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
