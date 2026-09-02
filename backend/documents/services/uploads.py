"""
Accepting an uploaded file.

Uploading is never a plain model save: a new file becomes the next version of
an existing document, the monograph's timeline gains an entry, and the
supervisor is told. Doing that in one place is what keeps the version history
trustworthy.
"""
import logging

from django.db import transaction

from core.enums import DocumentType
from core.exceptions import DomainError
from documents.models import Document, DocumentVersion
from monographs.services.transitions import log_activity

logger = logging.getLogger(__name__)


@transaction.atomic
def upload_version(
    monograph,
    user,
    uploaded_file,
    document_type: str,
    title: str = "",
    chapter_number: int | None = None,
    change_note: str = "",
    document: Document | None = None,
) -> DocumentVersion:
    """
    Store a file as the next version of a document.

    When no document is given, one is found or created for this type — so a
    student re-uploading their proposal extends the existing history instead
    of starting a second, competing document.
    """
    if monograph.academic_year.is_closed:
        raise DomainError("This academic year is closed and no longer accepts submissions.")

    if document is None:
        document = _find_or_create_document(
            monograph, document_type, title, chapter_number, user
        )

    version = DocumentVersion(
        document=document,
        version_number=document.next_version_number(),
        file=uploaded_file,
        original_filename=uploaded_file.name,
        content_type=getattr(uploaded_file, "content_type", ""),
        change_note=change_note,
        uploaded_by=user,
        created_by=user,
    )
    version.full_clean(exclude=["file"])  # validators run on the field below
    version.save()

    # A corrected file means the previous approval no longer applies.
    if document.is_approved and version.version_number > 1:
        document.is_approved = False
        document.approved_at = None
        document.approved_by = None
        document.save(update_fields=["is_approved", "approved_at", "approved_by"])

    log_activity(
        monograph,
        user,
        action="document_uploaded",
        description=f"{document.title} uploaded (version {version.version_number}).",
        document_id=str(document.id),
        document_type=document.document_type,
        version=version.version_number,
    )

    transaction.on_commit(lambda: _announce(monograph, version, user))
    return version


def _find_or_create_document(monograph, document_type, title, chapter_number, user):
    """
    The document a new file belongs to.

    Chapters are matched by number so chapter 2 version 3 lands on the right
    document; everything else is matched by type, because a monograph has only
    one proposal and one final copy.
    """
    lookup = {"monograph": monograph, "document_type": document_type}
    if document_type == DocumentType.CHAPTER:
        if chapter_number is None:
            raise DomainError("A chapter number is required when uploading a chapter.")
        lookup["chapter_number"] = chapter_number

    existing = Document.objects.filter(**lookup).first()
    if existing:
        return existing

    if not title:
        title = _default_title(document_type, chapter_number)

    return Document.objects.create(
        **lookup, title=title, created_by=user
    )


def _default_title(document_type: str, chapter_number: int | None) -> str:
    if document_type == DocumentType.CHAPTER and chapter_number:
        return f"Chapter {chapter_number}"
    return dict(DocumentType.choices).get(document_type, "Document")


def _announce(monograph, version, user):
    from documents.realtime import broadcast_document_uploaded
    from notifications.services import notify_document_uploaded

    try:
        notify_document_uploaded(version, user)
    except Exception:  # noqa: BLE001 - never undo an upload over a notice
        logger.exception("Failed to notify about upload %s", version.id)
    try:
        broadcast_document_uploaded(monograph, version)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to broadcast upload %s", version.id)


def can_access_document(document, user) -> bool:
    """
    Who may open a file.

    Deliberately the same rule as seeing the monograph: if a person can see
    the record, they can read its documents; if not, the file does not exist
    as far as they are concerned.
    """
    return document.monograph.is_visible_to(user)


def can_upload_to(monograph, user) -> bool:
    """
    Who may add files.

    Students upload their own work, supervisors and heads attach signed forms
    and corrected copies. A finished monograph accepts nothing further.
    """
    if monograph.is_finished:
        return False
    if user.is_admin:
        return True
    if monograph.members.filter(student=user).exists():
        return True
    if monograph.supervisor_id == user.id:
        return True
    if user.is_head_of_department:
        return monograph.department_id in user.headed_departments.values_list("id", flat=True)
    return False
