"""
The rules of the monograph journey.

Every legal move is declared here, once. Views and services ask this module
whether something is allowed; they never decide for themselves. That keeps a
single answer to "can this happen" no matter which screen the request came
from.
"""
from dataclasses import dataclass, field

from core.enums import MonographStage as S
from core.enums import Role


@dataclass(frozen=True)
class Transition:
    """One legal move between two stages."""

    source: str
    target: str
    #: Roles permitted to make this move.
    allowed_roles: tuple = ()
    #: Human wording used in the timeline and in notifications.
    label: str = ""
    #: Whether the actor must supply a note (rejections and revisions must).
    requires_note: bool = False
    #: Extra conditions checked against the monograph before allowing it.
    guards: tuple = field(default_factory=tuple)


STUDENT = Role.STUDENT
SUPERVISOR = Role.SUPERVISOR
HOD = Role.HEAD_OF_DEPARTMENT
ADMIN = Role.ADMIN

SUPERVISING = (SUPERVISOR, HOD)


TRANSITIONS: tuple[Transition, ...] = (
    # -- Getting the topic approved ---------------------------------------
    Transition(
        S.DRAFT, S.TOPIC_SUBMITTED,
        allowed_roles=(STUDENT,),
        label="Topic submitted for approval",
        guards=("has_title", "has_research_area"),
    ),
    Transition(
        S.TOPIC_SUBMITTED, S.TOPIC_APPROVED,
        allowed_roles=(HOD,),
        label="Topic approved",
        guards=("topic_votes_satisfied", "has_supervisor"),
    ),
    Transition(
        S.TOPIC_SUBMITTED, S.DRAFT,
        allowed_roles=(HOD,),
        label="Topic returned for changes",
        requires_note=True,
    ),
    Transition(
        S.TOPIC_SUBMITTED, S.REJECTED,
        allowed_roles=(HOD,),
        label="Topic rejected",
        requires_note=True,
    ),

    # -- The proposal ------------------------------------------------------
    Transition(
        S.TOPIC_APPROVED, S.PROPOSAL_SUBMITTED,
        allowed_roles=(STUDENT,),
        label="Proposal submitted",
        guards=("has_proposal_document",),
    ),
    Transition(
        S.PROPOSAL_SUBMITTED, S.UNDER_REVIEW,
        allowed_roles=SUPERVISING,
        label="Supervisor started reviewing",
    ),
    Transition(
        S.UNDER_REVIEW, S.REVISION_REQUIRED,
        allowed_roles=SUPERVISING,
        label="Revision requested",
        requires_note=True,
    ),
    Transition(
        S.UNDER_REVIEW, S.PROPOSAL_APPROVED,
        allowed_roles=SUPERVISING,
        label="Proposal approved",
    ),
    Transition(
        S.UNDER_REVIEW, S.REJECTED,
        allowed_roles=(HOD,),
        label="Proposal rejected",
        requires_note=True,
    ),
    # The revision loop: a student fixes the work and submits again. This may
    # repeat any number of times and every round is recorded.
    Transition(
        S.REVISION_REQUIRED, S.PROPOSAL_SUBMITTED,
        allowed_roles=(STUDENT,),
        label="Revised proposal submitted",
        guards=("has_proposal_document",),
    ),

    # -- Doing the research ------------------------------------------------
    Transition(
        S.PROPOSAL_APPROVED, S.RESEARCH_IN_PROGRESS,
        allowed_roles=(STUDENT,) + SUPERVISING,
        label="Research started",
    ),
    Transition(
        S.RESEARCH_IN_PROGRESS, S.FINAL_SUBMISSION,
        allowed_roles=(STUDENT,),
        label="Final monograph submitted",
        guards=("has_final_document",),
    ),

    # -- Final review ------------------------------------------------------
    Transition(
        S.FINAL_SUBMISSION, S.FINAL_REVIEW,
        allowed_roles=SUPERVISING,
        label="Final review started",
    ),
    Transition(
        S.FINAL_REVIEW, S.RESEARCH_IN_PROGRESS,
        allowed_roles=SUPERVISING,
        label="Sent back for more work",
        requires_note=True,
    ),
    Transition(
        S.FINAL_REVIEW, S.DEFENSE_SCHEDULED,
        allowed_roles=(HOD,),
        label="Defense scheduled",
        guards=("has_defense", "has_committee"),
    ),

    # -- Defense and archive ----------------------------------------------
    Transition(
        S.DEFENSE_SCHEDULED, S.DEFENDED,
        allowed_roles=(HOD,),
        label="Defense held",
        guards=("has_all_scores",),
    ),
    Transition(
        S.DEFENDED, S.COMPLETED,
        allowed_roles=(HOD,),
        label="Monograph completed and archived",
        guards=("has_final_grade",),
    ),
    Transition(
        S.DEFENDED, S.RESEARCH_IN_PROGRESS,
        allowed_roles=(HOD,),
        label="Returned after defense for corrections",
        requires_note=True,
    ),
    Transition(
        S.DEFENDED, S.REJECTED,
        allowed_roles=(HOD,),
        label="Failed the defense",
        requires_note=True,
    ),
)


#: Stages a student may withdraw from. Once a defense is scheduled the
#: department is committed, so withdrawal after that is an administrator's
#: decision rather than the student's.
WITHDRAWABLE_FROM = (
    S.DRAFT,
    S.TOPIC_SUBMITTED,
    S.TOPIC_APPROVED,
    S.PROPOSAL_SUBMITTED,
    S.UNDER_REVIEW,
    S.REVISION_REQUIRED,
    S.PROPOSAL_APPROVED,
    S.RESEARCH_IN_PROGRESS,
)

for _stage in WITHDRAWABLE_FROM:
    TRANSITIONS += (
        Transition(
            _stage, S.WITHDRAWN,
            allowed_roles=(STUDENT, HOD),
            label="Withdrawn",
            requires_note=True,
        ),
    )


# Index for fast lookup: (source, target) -> Transition
_BY_PAIR = {(t.source, t.target): t for t in TRANSITIONS}
_BY_SOURCE: dict[str, list[Transition]] = {}
for _t in TRANSITIONS:
    _BY_SOURCE.setdefault(_t.source, []).append(_t)


def get_transition(source: str, target: str) -> Transition | None:
    return _BY_PAIR.get((source, target))


def transitions_from(source: str) -> list[Transition]:
    return _BY_SOURCE.get(source, [])


def available_transitions(monograph, user) -> list[Transition]:
    """
    Which moves this person can make on this monograph right now.

    Drives the action buttons in the UI, so a student never sees a button that
    would be rejected by the server.
    """
    if monograph.is_finished:
        return []

    result = []
    for transition in transitions_from(monograph.stage):
        allowed, _reason = can_transition(monograph, user, transition.target)
        if allowed:
            result.append(transition)
    return result


#: Why a transition was refused. Callers map these to HTTP status codes:
#: a role failure is 403, everything else is 400.
DENIED_NO_SUCH_MOVE = "no_such_move"
DENIED_ROLE = "role"
DENIED_GUARD = "guard"


def check_transition(monograph, user, target: str) -> tuple[bool, str, str]:
    """
    Whether a move is allowed, why not, and which kind of check failed.

    Returns (ok, reason, denial_kind). The denial kind lets the caller tell
    "you are not allowed" apart from "that is not possible right now".
    """
    transition = get_transition(monograph.stage, target)
    if transition is None:
        return (
            False,
            f"A monograph at stage '{monograph.stage}' cannot move to '{target}'.",
            DENIED_NO_SUCH_MOVE,
        )

    if not _role_allowed(monograph, user, transition):
        return False, "Your role does not allow this action on this monograph.", DENIED_ROLE

    for guard in transition.guards:
        ok, reason = GUARDS[guard](monograph)
        if not ok:
            return False, reason, DENIED_GUARD

    return True, "", ""


def can_transition(monograph, user, target: str) -> tuple[bool, str]:
    """Convenience wrapper for callers that do not care why."""
    ok, reason, _kind = check_transition(monograph, user, target)
    return ok, reason


def _role_allowed(monograph, user, transition: Transition) -> bool:
    """
    Role check plus the relationship check.

    Being a supervisor is not enough — it must be *this* monograph's
    supervisor. Likewise a head of department may only act on monographs in a
    department they actually head.
    """
    if user.is_admin:
        return True
    if user.role not in transition.allowed_roles:
        return False

    if user.role == STUDENT:
        return monograph.members.filter(student=user).exists()

    if user.role == SUPERVISOR:
        return monograph.supervisor_id == user.id

    if user.role == HOD:
        # A head of department may also be acting as the supervisor.
        if monograph.supervisor_id == user.id:
            return True
        return monograph.department_id in user.headed_departments.values_list("id", flat=True)

    return False


# ---------------------------------------------------------------------------
# Guards: conditions that must hold before a move is allowed.
# Each returns (ok, reason).
# ---------------------------------------------------------------------------

def _has_title(m):
    if not m.title.strip():
        return False, "A title is required before submitting the topic."
    return True, ""


def _has_research_area(m):
    if m.research_area_id is None:
        return False, "Choose a research area before submitting."
    return True, ""


def _has_supervisor(m):
    if m.supervisor_id is None:
        return False, "Assign a supervisor before approving the topic."
    return True, ""


def _topic_votes_satisfied(m):
    from core.enums import TopicApprovalMode

    policy = m.policy
    if policy is None or policy.topic_approval_mode == TopicApprovalMode.HEAD_ONLY:
        return True, ""

    approvals = m.topic_votes.filter(approved=True).count()
    needed = policy.topic_approval_votes_required
    if approvals < needed:
        return False, f"This topic needs {needed} approvals and has {approvals}."
    return True, ""


def _has_document(m, doc_type, message):
    if not m.documents.filter(document_type=doc_type, is_deleted=False).exists():
        return False, message
    return True, ""


def _has_proposal_document(m):
    from core.enums import DocumentType

    return _has_document(m, DocumentType.PROPOSAL, "Upload the proposal before submitting.")


def _has_final_document(m):
    from core.enums import DocumentType

    return _has_document(
        m, DocumentType.FINAL_MONOGRAPH, "Upload the final monograph before submitting."
    )


def _has_defense(m):
    if getattr(m, "defense", None) is None:
        return False, "Schedule the defense first."
    return True, ""


def _has_committee(m):
    defense = getattr(m, "defense", None)
    if defense is None:
        return False, "Schedule the defense first."
    policy = m.policy
    required = policy.committee_size if policy else 3
    actual = defense.committee.count()
    if actual < required:
        return False, f"The committee needs {required} members and has {actual}."
    return True, ""


def _has_all_scores(m):
    defense = getattr(m, "defense", None)
    if defense is None:
        return False, "Schedule the defense first."
    missing = defense.committee.filter(score__isnull=True).count()
    if missing:
        return False, f"{missing} committee member(s) have not entered a score yet."
    return True, ""


def _has_final_grade(m):
    if m.final_grade is None:
        return False, "Record the final grade before completing."
    return True, ""


GUARDS = {
    "has_title": _has_title,
    "has_research_area": _has_research_area,
    "has_supervisor": _has_supervisor,
    "topic_votes_satisfied": _topic_votes_satisfied,
    "has_proposal_document": _has_proposal_document,
    "has_final_document": _has_final_document,
    "has_defense": _has_defense,
    "has_committee": _has_committee,
    "has_all_scores": _has_all_scores,
    "has_final_grade": _has_final_grade,
}
