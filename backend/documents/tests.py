"""Uploads, versions, and who may open a file."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from core.enums import DocumentType
from documents.services.uploads import can_access_document, can_upload_to, upload_version


def a_file(name="proposal.pdf", size=1024):
    return SimpleUploadedFile(name, b"%PDF-1.4\n" + b"x" * size, "application/pdf")


@pytest.mark.django_db
class TestVersioning:
    def test_uploading_again_adds_a_version_rather_than_replacing(
        self, supervised, student
    ):
        """Nothing a student submits is ever overwritten."""
        first = upload_version(
            supervised, student, a_file(), DocumentType.PROPOSAL, title="Proposal"
        )
        second = upload_version(
            supervised, student, a_file("proposal_v2.pdf"),
            DocumentType.PROPOSAL, change_note="Narrowed the objectives.",
        )

        assert first.document_id == second.document_id
        assert (first.version_number, second.version_number) == (1, 2)
        assert first.document.version_count == 2
        assert first.document.current_version.id == second.id

    def test_the_earlier_version_stays_readable(self, supervised, student):
        first = upload_version(
            supervised, student, a_file(), DocumentType.PROPOSAL, title="Proposal"
        )
        upload_version(supervised, student, a_file("v2.pdf"), DocumentType.PROPOSAL)

        first.refresh_from_db()
        assert first.file  # still on disk, still linked

    def test_chapters_are_kept_apart_by_number(self, supervised, student):
        one = upload_version(
            supervised, student, a_file("ch1.pdf"), DocumentType.CHAPTER, chapter_number=1
        )
        two = upload_version(
            supervised, student, a_file("ch2.pdf"), DocumentType.CHAPTER, chapter_number=2
        )
        assert one.document_id != two.document_id

    def test_a_correction_withdraws_an_earlier_approval(self, supervised, student, supervisor):
        """An approved document that changes must be looked at again."""
        from django.utils import timezone

        version = upload_version(
            supervised, student, a_file(), DocumentType.PROPOSAL, title="Proposal"
        )
        document = version.document
        document.is_approved = True
        document.approved_at = timezone.now()
        document.approved_by = supervisor
        document.save()

        upload_version(supervised, student, a_file("v2.pdf"), DocumentType.PROPOSAL)

        document.refresh_from_db()
        assert not document.is_approved

    def test_each_upload_is_fingerprinted(self, supervised, student):
        """Proves a file has not been swapped for a different one."""
        version = upload_version(
            supervised, student, a_file(), DocumentType.PROPOSAL, title="Proposal"
        )
        assert len(version.checksum) == 64


@pytest.mark.django_db
class TestAccess:
    def test_the_people_involved_may_open_a_file(
        self, supervised, student, supervisor, hod
    ):
        version = upload_version(
            supervised, student, a_file(), DocumentType.PROPOSAL, title="Proposal"
        )
        for person in (student, supervisor, hod):
            assert can_access_document(version.document, person)

    def test_an_unrelated_student_may_not(self, supervised, student, other_student):
        version = upload_version(
            supervised, student, a_file(), DocumentType.PROPOSAL, title="Proposal"
        )
        assert not can_access_document(version.document, other_student)

    def test_a_missing_file_and_a_forbidden_one_look_the_same(
        self, as_user, supervised, student, other_student
    ):
        """
        Someone who may not read a file should not learn that it exists, so
        the answer is 404 rather than 403.
        """
        version = upload_version(
            supervised, student, a_file(), DocumentType.PROPOSAL, title="Proposal"
        )
        response = as_user(other_student).get(
            f"/api/v1/documents/versions/{version.id}/download/"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nothing_may_be_added_to_a_finished_monograph(
        self, supervised, student
    ):
        from core.enums import MonographStage

        supervised.stage = MonographStage.COMPLETED
        supervised.save()
        assert not can_upload_to(supervised, student)

    def test_an_unrelated_student_may_not_upload(self, supervised, other_student):
        assert not can_upload_to(supervised, other_student)


@pytest.mark.django_db
class TestUploadRules:
    def test_a_closed_year_accepts_nothing_further(self, supervised, student, year):
        from core.exceptions import DomainError

        year.is_closed = True
        year.save()
        supervised.refresh_from_db()

        with pytest.raises(DomainError):
            upload_version(
                supervised, student, a_file(), DocumentType.PROPOSAL, title="Proposal"
            )

    def test_a_chapter_needs_its_number(self, supervised, student):
        from core.exceptions import DomainError

        with pytest.raises(DomainError):
            upload_version(supervised, student, a_file(), DocumentType.CHAPTER)
