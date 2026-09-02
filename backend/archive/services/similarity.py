"""
Checking whether a topic has been written before.

This is a duplicate check inside the department's own records, not plagiarism
detection against the internet. It exists to stop two students unknowingly
writing the same monograph, or one repeating work done three years earlier.

The comparison is deliberately simple and local: it runs on a machine inside
the university with no internet, so it uses word overlap rather than any
external service.
"""
import re
from collections import Counter

#: Words too common in academic titles to tell anything apart.
STOP_WORDS = {
    "a", "an", "and", "the", "of", "in", "on", "for", "to", "with", "by",
    "using", "based", "study", "analysis", "system", "research", "approach",
    "method", "methods", "application", "applications", "development", "design",
    "implementation", "evaluation", "investigation", "review", "case", "new",
    "novel", "improved", "towards", "toward", "into", "from", "at", "as", "is",
    "are", "its", "their", "this", "that", "these", "those", "it",
}


def tokenise(text: str) -> set[str]:
    """Meaningful words from a title or abstract, lowercased."""
    if not text:
        return set()
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOP_WORDS}


def similarity_score(first: str, second: str) -> int:
    """
    How alike two pieces of text are, as a percentage.

    Uses Jaccard overlap — shared words divided by total distinct words. Crude,
    but it reliably catches the case this is for: the same topic worded
    slightly differently.
    """
    a, b = tokenise(first), tokenise(second)
    if not a or not b:
        return 0
    shared = a & b
    union = a | b
    return round(len(shared) / len(union) * 100)


def find_similar(monograph, limit: int = 5) -> list[dict]:
    """
    Existing monographs that resemble this one.

    Looks at the department's own work only — past years and the current one —
    because a topic being common elsewhere is not the department's problem.
    """
    from monographs.models import Monograph

    policy = getattr(monograph.department, "policy", None)
    threshold = policy.similarity_threshold if policy else 60

    candidates = (
        Monograph.objects.filter(department=monograph.department)
        .exclude(pk=monograph.pk)
        .exclude(stage__in=["withdrawn", "rejected"])
        .select_related("academic_year")
        .prefetch_related("members__student")
    )

    subject = f"{monograph.title} {monograph.abstract}"
    matches = []
    for other in candidates:
        score = similarity_score(subject, f"{other.title} {other.abstract}")
        if score >= threshold:
            shared = tokenise(subject) & tokenise(f"{other.title} {other.abstract}")
            matches.append(
                {
                    "monograph_id": str(other.id),
                    "title": other.title,
                    "students": other.student_names,
                    "academic_year": other.academic_year.name,
                    "stage": other.stage,
                    "score": score,
                    "matched_terms": sorted(shared)[:10],
                }
            )

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:limit]


def record_similarities(monograph) -> int:
    """
    Save the matches so the head of department sees them when approving.

    Stored rather than recomputed on every screen because the check runs over
    every monograph in the department and only changes when a topic changes.
    """
    from archive.models import TopicSimilarity
    from monographs.models import Monograph

    found = find_similar(monograph, limit=10)
    created = 0
    for match in found:
        other = Monograph.objects.filter(pk=match["monograph_id"]).first()
        if other is None:
            continue
        _row, was_created = TopicSimilarity.objects.update_or_create(
            monograph=monograph,
            similar_to=other,
            defaults={
                "score": match["score"],
                "matched_terms": match["matched_terms"],
            },
        )
        created += int(was_created)
    return created


def archive_monograph(monograph, user=None):
    """
    Copy a finished monograph into the permanent library.

    Names and titles are copied as plain text so the entry stays readable in
    ten years, after accounts are deactivated and departments renamed.
    """
    from archive.models import ArchiveEntry
    from core.enums import DocumentType

    final_version = None
    final_document = monograph.documents.filter(
        document_type=DocumentType.FINAL_MONOGRAPH
    ).first()
    if final_document:
        final_version = final_document.current_version

    defense = getattr(monograph, "defense", None)

    entry, _created = ArchiveEntry.objects.update_or_create(
        monograph=monograph,
        defaults={
            "title": monograph.title,
            "abstract": monograph.abstract,
            "keywords": monograph.keywords,
            "author_names": monograph.student_names,
            "supervisor_name": monograph.supervisor.display_name if monograph.supervisor else "",
            "department_name": monograph.department.name,
            "academic_year_name": monograph.academic_year.name,
            "research_area_name": monograph.research_area.name if monograph.research_area else "",
            "final_grade": monograph.final_grade,
            "defended_on": defense.held_at.date() if defense and defense.held_at else None,
            "final_document": final_version,
            "created_by": user,
        },
    )
    return entry
