"""
Uploaded files and their version history.

Two rules from the requirements shape this whole app:

1. Nothing is ever deleted. When a student uploads a corrected chapter the
   old file stays beside it as version 1, 2, 3 and so on.
2. Files are never served directly by the web server. Every download goes
   through a permission check, because a monograph draft is private to the
   people involved with it.
"""
import hashlib
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models

from core.enums import DocumentType
from core.models import BaseModel

#: Storage that writes outside the public media root. Nothing here is
#: reachable by URL without passing through documents.views.DownloadView.
private_storage = FileSystemStorage(location=str(settings.PRIVATE_MEDIA_ROOT))


def upload_path(instance, filename: str) -> str:
    """
    Where a version's file lands on disk.

    Grouped by monograph then document so a department can find or back up one
    student's work by copying a single folder.

    Ids are shortened to their first segment: the full pair of UUIDs pushed
    the path past the field limit, and within one monograph's folder the short
    form is still unique. The version number keeps files from colliding.
    """
    ext = os.path.splitext(filename)[1].lower()[:10]
    monograph_ref = str(instance.document.monograph_id)[:8]
    document_ref = str(instance.document_id)[:8]
    return (
        f"monographs/{monograph_ref}/"
        f"{instance.document.document_type}/"
        f"{document_ref}_v{instance.version_number}{ext}"
    )


def validate_upload(file):
    """Reject files that are too large or of a type the university does not accept."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            f"File is {file.size // (1024 * 1024)} MB. The limit is {settings.MAX_UPLOAD_SIZE_MB} MB."
        )
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_UPLOAD_EXTENSIONS)
        raise ValidationError(f"'{ext}' files are not accepted. Allowed types: {allowed}.")


class Document(BaseModel):
    """
    One logical document on a monograph — "the proposal", "chapter 3".

    The file itself lives in DocumentVersion. This row is the stable thing a
    review points at, so feedback stays attached even after the student
    uploads a corrected file.
    """

    monograph = models.ForeignKey(
        "monographs.Monograph", on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(
        max_length=32, choices=DocumentType.choices, db_index=True
    )
    title = models.CharField(max_length=255)

    #: Chapter number, when this is a chapter. Lets the UI list them in order.
    chapter_number = models.PositiveIntegerField(null=True, blank=True)

    description = models.TextField(blank=True)

    #: Set once the supervisor approves this particular document.
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_documents",
    )

    class Meta:
        ordering = ("document_type", "chapter_number", "created_at")
        indexes = [
            models.Index(fields=["monograph", "document_type"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"

    @property
    def current_version(self):
        """The newest version, which is what people mean by "the document"."""
        return self.versions.order_by("-version_number").first()

    @property
    def version_count(self) -> int:
        return self.versions.count()

    def next_version_number(self) -> int:
        latest = self.versions.order_by("-version_number").first()
        return (latest.version_number + 1) if latest else 1


class DocumentVersion(BaseModel):
    """
    One uploaded file.

    Immutable once written: a new upload creates a new row rather than
    replacing this one, so the trail of what was submitted when survives
    intact.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()

    file = models.FileField(
        upload_to=upload_path,
        storage=private_storage,
        validators=[validate_upload],
        max_length=255,
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=128, blank=True)

    #: Detects an identical re-upload, and proves a file has not been swapped.
    checksum = models.CharField(max_length=64, blank=True, db_index=True)

    #: What the student says changed since the previous version.
    change_note = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="uploads"
    )

    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-version_number",)
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="unique_version_per_document",
            )
        ]

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"

    def save(self, *args, **kwargs):
        if self.file and not self.checksum:
            self.file_size = self.file.size
            self.checksum = self._compute_checksum()
        super().save(*args, **kwargs)

    def _compute_checksum(self) -> str:
        digest = hashlib.sha256()
        for chunk in self.file.chunks():
            digest.update(chunk)
        # Rewind so the storage backend writes from the start.
        self.file.seek(0)
        return digest.hexdigest()

    @property
    def size_display(self) -> str:
        size = float(self.file_size)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def extension(self) -> str:
        return os.path.splitext(self.original_filename)[1].lower().lstrip(".")


class DownloadLog(BaseModel):
    """
    Who opened which file and when.

    Kept because supervisors and students sometimes disagree about whether
    work was ever collected, and because the department head should be able
    to see that an examiner actually read the monograph before the defense.
    """

    version = models.ForeignKey(
        DocumentVersion, on_delete=models.CASCADE, related_name="downloads"
    )
    user = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="downloads"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        who = self.user.full_name if self.user else "unknown"
        return f"{who} downloaded {self.version}"
