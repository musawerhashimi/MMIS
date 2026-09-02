"""
The numbers each role needs to see.

Every figure here answers a question someone actually asks: "how many students
are behind?", "who is waiting on me?", "where is the department stuck?".
Nothing is stored — it is all computed from the monograph tables at read time,
so the dashboard can never drift out of step with reality.
"""
from datetime import timedelta

from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from core.enums import FINISHED_STAGES, MonographStage, Role, stage_progress_percent
from monographs.models import Monograph, StageTransition


def _base_queryset(user, department=None, academic_year=None):
    queryset = Monograph.objects.visible_to(user)
    if department:
        queryset = queryset.filter(department_id=department)
    if academic_year:
        queryset = queryset.filter(academic_year_id=academic_year)
    return queryset


def department_overview(user, department=None, academic_year=None) -> dict:
    """
    The head of department's main screen.

    Answers the question that used to require ringing every supervisor: where
    is everyone, and who needs attention today.
    """
    queryset = _base_queryset(user, department, academic_year)
    active = queryset.exclude(stage__in=FINISHED_STAGES)

    policy = _policy_for(department)
    response_days = policy.supervisor_response_days if policy else 7
    inactivity_days = policy.student_inactivity_days if policy else 30

    now = timezone.now()
    waiting_cutoff = now - timedelta(days=response_days)
    quiet_cutoff = now - timedelta(days=inactivity_days)

    awaiting_stages = [
        MonographStage.PROPOSAL_SUBMITTED,
        MonographStage.UNDER_REVIEW,
        MonographStage.FINAL_SUBMISSION,
        MonographStage.FINAL_REVIEW,
    ]

    return {
        "totals": {
            "total": queryset.count(),
            "active": active.count(),
            "completed": queryset.filter(stage=MonographStage.COMPLETED).count(),
            "rejected": queryset.filter(stage=MonographStage.REJECTED).count(),
            "withdrawn": queryset.filter(stage=MonographStage.WITHDRAWN).count(),
            "unassigned": active.filter(supervisor__isnull=True).count(),
        },
        "attention": {
            # Submitted work nobody has answered within the department's own
            # agreed response time.
            "awaiting_supervisor": active.filter(
                stage__in=awaiting_stages, stage_changed_at__lt=waiting_cutoff
            ).count(),
            # Students who have not moved in a long time.
            "gone_quiet": active.filter(stage_changed_at__lt=quiet_cutoff).count(),
            "behind_deadline": _behind_deadline_count(active, department, academic_year),
        },
        "by_stage": stage_breakdown(queryset),
        "supervisor_load": supervisor_workload(user, department, academic_year),
        "bottlenecks": stage_durations(queryset),
        "recent_activity": _recent_transitions(queryset),
    }


def stage_breakdown(queryset) -> list[dict]:
    """
    How many monographs sit at each stage.

    Every stage is returned, including empty ones: a stage with nobody in it
    is as informative as a crowded one.
    """
    counts = dict(
        queryset.values_list("stage").annotate(n=Count("id")).values_list("stage", "n")
    )
    total = sum(counts.values()) or 1
    return [
        {
            "stage": stage,
            "label": label,
            "count": counts.get(stage, 0),
            "percent": round(counts.get(stage, 0) / total * 100, 1),
            "progress": stage_progress_percent(stage),
            "is_finished": stage in FINISHED_STAGES,
        }
        for stage, label in MonographStage.choices
    ]


def supervisor_workload(user, department=None, academic_year=None) -> list[dict]:
    """
    How many students each supervisor is carrying.

    This is the report that exposes the uneven loading nobody planned — one
    professor with twenty-five students while another has three.
    """
    from accounts.models import User

    supervisors = User.objects.filter(
        role__in=[Role.SUPERVISOR, Role.HEAD_OF_DEPARTMENT], is_active=True
    ).select_related("supervisor_profile")
    if department:
        supervisors = supervisors.filter(department_id=department)

    rows = []
    for supervisor in supervisors:
        monographs = Monograph.objects.filter(supervisor=supervisor)
        if academic_year:
            monographs = monographs.filter(academic_year_id=academic_year)

        active = monographs.exclude(stage__in=FINISHED_STAGES)
        profile = getattr(supervisor, "supervisor_profile", None)
        capacity = profile.effective_max_students if profile else None
        active_count = active.count()

        rows.append(
            {
                "id": str(supervisor.id),
                "name": supervisor.display_name,
                "active": active_count,
                "completed": monographs.filter(stage=MonographStage.COMPLETED).count(),
                "capacity": capacity,
                "utilisation": round(active_count / capacity * 100) if capacity else None,
                "over_capacity": bool(capacity and active_count > capacity),
                "awaiting_response": active.filter(
                    stage__in=[
                        MonographStage.PROPOSAL_SUBMITTED,
                        MonographStage.UNDER_REVIEW,
                        MonographStage.FINAL_SUBMISSION,
                        MonographStage.FINAL_REVIEW,
                    ]
                ).count(),
            }
        )

    return sorted(rows, key=lambda row: row["active"], reverse=True)


def stage_durations(queryset) -> list[dict]:
    """
    How long monographs typically spend at each stage.

    This is what shows the department where its real bottleneck is, rather
    than where people assume it is.
    """
    rows = (
        StageTransition.objects.filter(
            monograph__in=queryset, days_in_previous_stage__isnull=False
        )
        .values("from_stage")
        .annotate(average_days=Avg("days_in_previous_stage"), moves=Count("id"))
        .order_by("-average_days")
    )

    labels = dict(MonographStage.choices)
    return [
        {
            "stage": row["from_stage"],
            "label": labels.get(row["from_stage"], row["from_stage"]),
            "average_days": round(row["average_days"] or 0, 1),
            "sample_size": row["moves"],
        }
        for row in rows
        if row["from_stage"]
    ]


def supervisor_dashboard(user) -> dict:
    """
    The supervisor's first screen: what needs answering today.

    Ordered by how long people have been waiting, because the longest wait is
    usually the one that matters.
    """
    monographs = Monograph.objects.filter(supervisor=user)
    active = monographs.exclude(stage__in=FINISHED_STAGES)

    awaiting = active.filter(
        stage__in=[
            MonographStage.PROPOSAL_SUBMITTED,
            MonographStage.UNDER_REVIEW,
            MonographStage.FINAL_SUBMISSION,
            MonographStage.FINAL_REVIEW,
        ]
    ).order_by("stage_changed_at")

    quiet_cutoff = timezone.now() - timedelta(days=30)

    return {
        "totals": {
            "active": active.count(),
            "completed": monographs.filter(stage=MonographStage.COMPLETED).count(),
            "awaiting_me": awaiting.count(),
        },
        "awaiting_me": [
            {
                "id": str(m.id),
                "title": m.title,
                "students": m.student_names,
                "stage": m.stage,
                "stage_label": m.get_stage_display(),
                "waiting_days": m.days_in_current_stage,
            }
            for m in awaiting[:10]
        ],
        "gone_quiet": [
            {
                "id": str(m.id),
                "title": m.title,
                "students": m.student_names,
                "stage_label": m.get_stage_display(),
                "silent_days": m.days_in_current_stage,
            }
            for m in active.filter(stage_changed_at__lt=quiet_cutoff)[:10]
        ],
        "by_stage": stage_breakdown(monographs),
    }


def student_dashboard(user) -> dict:
    """
    What a student needs: where am I, what is expected, what did I get back.
    """
    monograph = (
        Monograph.objects.filter(members__student=user)
        .select_related("supervisor", "department", "research_area")
        .order_by("-created_at")
        .first()
    )
    if monograph is None:
        return {"monograph": None}

    latest_review = monograph.reviews.select_related("reviewer").first()
    defense = getattr(monograph, "defense", None)
    deadline = _next_deadline(monograph)

    return {
        "monograph": {
            "id": str(monograph.id),
            "title": monograph.title,
            "stage": monograph.stage,
            "stage_label": monograph.get_stage_display(),
            "progress_percent": monograph.progress_percent,
            "days_in_current_stage": monograph.days_in_current_stage,
            "supervisor": monograph.supervisor.display_name if monograph.supervisor else None,
        },
        "latest_feedback": (
            {
                "decision": latest_review.decision,
                "summary": latest_review.summary,
                "comments": latest_review.comments,
                "reviewer": latest_review.reviewer.full_name,
                "at": latest_review.created_at.isoformat(),
            }
            if latest_review
            else None
        ),
        "next_deadline": deadline,
        "defense": (
            {
                "scheduled_at": defense.scheduled_at.isoformat() if defense.scheduled_at else None,
                "location": defense.location,
                "result": defense.result,
                "final_grade": str(defense.final_grade) if defense.final_grade else None,
            }
            if defense
            else None
        ),
        "documents": monograph.documents.count(),
        "unread_notifications": user.notifications.filter(read_at__isnull=True).count(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _policy_for(department_id):
    if not department_id:
        return None
    from organization.models import DepartmentPolicy

    return DepartmentPolicy.objects.filter(department_id=department_id).first()


def _behind_deadline_count(active_queryset, department, academic_year) -> int:
    """
    How many monographs have missed the date they were meant to reach.

    A monograph is behind if a deadline has passed and it has not yet reached
    the stage that deadline was for. Counted with one query per overdue
    deadline rather than per monograph, because a department can hold hundreds
    of records and this runs on every dashboard load.

    Only departments that actually set deadlines are measured; where each
    supervisor sets their own dates there is nothing to compare against.
    """
    from core.enums import STAGE_ORDER, stage_index
    from organization.models import StageDeadline

    deadlines = StageDeadline.objects.all()
    if department:
        deadlines = deadlines.filter(department_id=department)
    if academic_year:
        deadlines = deadlines.filter(academic_year_id=academic_year)

    today = timezone.now().date()
    overdue = deadlines.filter(due_date__lt=today)
    if not overdue.exists():
        return 0

    # A monograph counts once even if it has missed several deadlines, so
    # collect ids rather than adding up per-deadline totals.
    behind_ids: set = set()
    for deadline in overdue:
        target_index = stage_index(deadline.stage)
        if target_index <= 0:
            continue
        # Stages that sit before the one that was due.
        earlier_stages = [str(stage) for stage in STAGE_ORDER[:target_index]]
        behind_ids.update(
            active_queryset.filter(
                department_id=deadline.department_id, stage__in=earlier_stages
            ).values_list("id", flat=True)
        )

    return len(behind_ids)


def _next_deadline(monograph) -> dict | None:
    from organization.models import StageDeadline

    deadline = (
        StageDeadline.objects.filter(
            department=monograph.department,
            academic_year=monograph.academic_year,
            due_date__gte=timezone.now().date(),
        )
        .order_by("due_date")
        .first()
    )
    if deadline is None:
        return None
    return {
        "stage": deadline.stage,
        "due_date": deadline.due_date.isoformat(),
        "days_remaining": (deadline.due_date - timezone.now().date()).days,
        "description": deadline.description,
    }


def _recent_transitions(queryset, limit: int = 15) -> list[dict]:
    rows = (
        StageTransition.objects.filter(monograph__in=queryset)
        .select_related("monograph", "actor")
        .order_by("-created_at")[:limit]
    )
    labels = dict(MonographStage.choices)
    return [
        {
            "monograph_id": str(row.monograph_id),
            "title": row.monograph.title,
            "to_stage": row.to_stage,
            "to_stage_label": labels.get(row.to_stage, row.to_stage),
            "actor": row.actor.full_name if row.actor else None,
            "at": row.created_at.isoformat(),
        }
        for row in rows
    ]
