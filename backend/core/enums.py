"""
Shared vocabulary for the whole system.

Every stage name, role and decision in the product description appears here
exactly once. Nothing else in the codebase should invent its own strings.
"""
from django.db import models


class Role(models.TextChoices):
    """Who someone is in the department."""

    STUDENT = "student", "Student"
    SUPERVISOR = "supervisor", "Supervisor"
    HEAD_OF_DEPARTMENT = "hod", "Head of Department"
    COMMITTEE_MEMBER = "committee", "Committee Member"
    ADMIN = "admin", "Administrator"


class MonographStage(models.TextChoices):
    """
    The thirteen stages of the monograph journey, plus the two endings.

    The numeric prefix keeps the natural ordering available for sorting and
    for "how far along is this student" progress maths, while the stored
    value stays a readable slug.
    """

    DRAFT = "draft", "Draft"
    TOPIC_SUBMITTED = "topic_submitted", "Topic Submitted"
    TOPIC_APPROVED = "topic_approved", "Topic Approved"
    PROPOSAL_SUBMITTED = "proposal_submitted", "Proposal Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    REVISION_REQUIRED = "revision_required", "Revision Required"
    PROPOSAL_APPROVED = "proposal_approved", "Proposal Approved"
    RESEARCH_IN_PROGRESS = "research_in_progress", "Research In Progress"
    FINAL_SUBMISSION = "final_submission", "Final Submission"
    FINAL_REVIEW = "final_review", "Final Review"
    DEFENSE_SCHEDULED = "defense_scheduled", "Defense Scheduled"
    DEFENDED = "defended", "Defended"
    COMPLETED = "completed", "Completed"

    # Terminal states reachable from several points in the journey.
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


#: Order used for progress bars and "which stage is further" comparisons.
#: Terminal states sit outside the ladder and are handled separately.
STAGE_ORDER = [
    MonographStage.DRAFT,
    MonographStage.TOPIC_SUBMITTED,
    MonographStage.TOPIC_APPROVED,
    MonographStage.PROPOSAL_SUBMITTED,
    MonographStage.UNDER_REVIEW,
    MonographStage.REVISION_REQUIRED,
    MonographStage.PROPOSAL_APPROVED,
    MonographStage.RESEARCH_IN_PROGRESS,
    MonographStage.FINAL_SUBMISSION,
    MonographStage.FINAL_REVIEW,
    MonographStage.DEFENSE_SCHEDULED,
    MonographStage.DEFENDED,
    MonographStage.COMPLETED,
]

TERMINAL_STAGES = {MonographStage.REJECTED, MonographStage.WITHDRAWN}
FINISHED_STAGES = TERMINAL_STAGES | {MonographStage.COMPLETED}


def stage_index(stage: str) -> int:
    """Position of a stage on the ladder, or -1 for terminal stages."""
    try:
        return STAGE_ORDER.index(MonographStage(stage))
    except ValueError:
        return -1


def stage_progress_percent(stage: str) -> int:
    """How far along the journey a monograph is, as a whole percentage."""
    if stage == MonographStage.COMPLETED:
        return 100
    idx = stage_index(stage)
    if idx < 0:
        return 0
    return round(idx / (len(STAGE_ORDER) - 1) * 100)


class DocumentType(models.TextChoices):
    """What a given uploaded file is."""

    TOPIC_FORM = "topic_form", "Topic Form"
    PROPOSAL = "proposal", "Proposal"
    CHAPTER = "chapter", "Chapter"
    FINAL_MONOGRAPH = "final_monograph", "Final Monograph"
    PRESENTATION = "presentation", "Defense Presentation"
    SUPPORTING = "supporting", "Supporting Material"
    SIGNED_FORM = "signed_form", "Signed Official Form"


class ReviewDecision(models.TextChoices):
    """The three answers a supervisor can give."""

    APPROVED = "approved", "Approved"
    REVISION_REQUESTED = "revision_requested", "Revision Requested"
    REJECTED = "rejected", "Rejected"


class DefenseResult(models.TextChoices):
    PASSED = "passed", "Passed"
    PASSED_WITH_REVISIONS = "passed_with_revisions", "Passed With Minor Revisions"
    FAILED = "failed", "Failed"


class CommitteeRole(models.TextChoices):
    CHAIR = "chair", "Chair"
    SUPERVISOR = "supervisor", "Supervisor"
    INTERNAL_EXAMINER = "internal", "Internal Examiner"
    EXTERNAL_EXAMINER = "external", "External Examiner"
    SECRETARY = "secretary", "Secretary"


class TopicApprovalMode(models.TextChoices):
    """
    How a department approves topics.

    Confirmed as varying between departments, so it is configuration rather
    than a hard-coded rule. See organization.models.DepartmentPolicy.
    """

    HEAD_ONLY = "head_only", "Head of Department decides alone"
    COMMITTEE_VOTE = "committee_vote", "Committee vote"


class SupervisorAssignmentMode(models.TextChoices):
    """How a student ends up with a supervisor."""

    ASSIGNED_BY_HEAD = "assigned_by_head", "Assigned by Head of Department"
    STUDENT_CHOOSES = "student_chooses", "Student chooses, Head confirms"
    STUDENT_PREFERENCE = "student_preference", "Student ranks preferences, Head decides"


class NotificationKind(models.TextChoices):
    """Grouping used for icons, colours and filtering in the UI."""

    STAGE_CHANGED = "stage_changed", "Stage Changed"
    REVIEW_RECEIVED = "review_received", "Review Received"
    SUBMISSION_RECEIVED = "submission_received", "Submission Received"
    DEADLINE_APPROACHING = "deadline_approaching", "Deadline Approaching"
    DEADLINE_MISSED = "deadline_missed", "Deadline Missed"
    DEFENSE_SCHEDULED = "defense_scheduled", "Defense Scheduled"
    SUPERVISOR_ASSIGNED = "supervisor_assigned", "Supervisor Assigned"
    ANNOUNCEMENT = "announcement", "Announcement"
