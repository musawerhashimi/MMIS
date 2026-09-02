"""
Producing the paper the university archive still requires.

This is not a nice-to-have. Staff need signed forms for the archive, and if
the system cannot produce them people will type the same information twice
into Word and quietly stop using the system. Every form here mirrors one the
department already fills in by hand.
"""
import logging
from datetime import datetime

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

#: Shown in the letterhead. Set UNIVERSITY_NAME in the environment so one
#: build can be installed at more than one university.
UNIVERSITY_NAME = getattr(settings, "UNIVERSITY_NAME", "University")


def render_pdf(template_name: str, context: dict) -> bytes:
    """
    Turn a template into a PDF.

    WeasyPrint is imported here rather than at module load: it pulls in large
    native libraries, and a system that never prints a form should not pay
    that cost at startup.
    """
    from weasyprint import HTML

    html = render_to_string(template_name, context)
    return HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()


def _base_context(monograph, reference_prefix: str) -> dict:
    """The letterhead and reference fields every form shares."""
    department = monograph.department
    students = list(monograph.members.select_related("student"))

    return {
        "university_name": UNIVERSITY_NAME,
        "faculty_name": department.faculty.name,
        "department_name": department.name,
        "reference": f"{reference_prefix}/{department.code}/{str(monograph.id)[:8].upper()}",
        "issued_on": timezone.now().strftime("%Y-%m-%d"),
        "generated_at": timezone.now().strftime("%Y-%m-%d %H:%M"),
        "students": students,
        "student_names": ", ".join(m.student.full_name for m in students),
        "student_ids": ", ".join(
            getattr(getattr(m.student, "student_profile", None), "student_id", "—")
            for m in students
        ),
        "title": monograph.title,
        "supervisor": monograph.supervisor.display_name if monograph.supervisor else "—",
        "head_of_department": department.head.display_name if department.head else "—",
        "academic_year": monograph.academic_year.name,
        "research_area": monograph.research_area.name if monograph.research_area else "—",
    }


def topic_approval_form(monograph) -> bytes:
    """The form that records a topic being accepted by the department."""
    from core.enums import MonographStage, stage_index

    approved = stage_index(monograph.stage) >= stage_index(MonographStage.TOPIC_APPROVED)
    approval_move = monograph.transitions.filter(
        to_stage=MonographStage.TOPIC_APPROVED
    ).first()

    context = {
        **_base_context(monograph, "TAF"),
        "abstract": monograph.abstract,
        "objectives": monograph.objectives,
        "methodology": monograph.methodology,
        "decision": "Approved" if approved else "Pending approval",
        "approved_on": (
            approval_move.created_at.strftime("%Y-%m-%d") if approval_move else "—"
        ),
    }
    return render_pdf("forms/topic_approval.html", context)


def supervisor_assignment_letter(monograph) -> bytes:
    """The letter appointing a supervisor to a student."""
    policy = getattr(monograph.department, "policy", None)
    profile = getattr(monograph.supervisor, "supervisor_profile", None)

    context = {
        **_base_context(monograph, "SAL"),
        "assigned_on": (
            monograph.supervisor_assigned_at.strftime("%Y-%m-%d")
            if monograph.supervisor_assigned_at
            else "—"
        ),
        "response_days": policy.supervisor_response_days if policy else 7,
        "current_load": profile.active_student_count if profile else 0,
    }
    return render_pdf("forms/supervisor_assignment.html", context)


def defense_notice(monograph) -> bytes:
    """The public notice announcing a defense."""
    defense = getattr(monograph, "defense", None)
    if defense is None:
        raise ValueError("This monograph has no scheduled defense.")

    context = {
        **_base_context(monograph, "DN"),
        "scheduled_at": (
            defense.scheduled_at.strftime("%Y-%m-%d at %H:%M")
            if defense.scheduled_at
            else "—"
        ),
        "location": defense.location or "To be confirmed",
        "duration": defense.duration_minutes,
        "committee": [
            {"name": seat.member.display_name, "role": seat.get_role_display()}
            for seat in defense.committee.select_related("member")
        ],
    }
    return render_pdf("forms/defense_notice.html", context)


def defense_result_sheet(monograph) -> bytes:
    """The signed record of the defense outcome and final grade."""
    defense = getattr(monograph, "defense", None)
    if defense is None:
        raise ValueError("This monograph has no defense on record.")

    policy = getattr(monograph.department, "policy", None)

    context = {
        **_base_context(monograph, "DRS"),
        "held_at": defense.held_at.strftime("%Y-%m-%d") if defense.held_at else "—",
        "location": defense.location or "—",
        "committee": [
            {
                "name": seat.member.display_name,
                "role": seat.get_role_display(),
                "score": seat.score,
            }
            for seat in defense.committee.select_related("member")
        ],
        "committee_average": defense.committee_average,
        "supervisor_score": defense.supervisor_score,
        "supervisor_weight": policy.supervisor_grade_weight if policy else 40,
        "final_grade": defense.final_grade,
        "result": defense.get_result_display() if defense.result else "Not recorded",
        "required_revisions": defense.required_revisions,
        "revisions_due_date": defense.revisions_due_date,
        "notes": defense.notes,
    }
    return render_pdf("forms/defense_result.html", context)


#: The forms a user can ask for, and what each needs to exist first.
AVAILABLE_FORMS = {
    "topic_approval": {
        "label": "Topic Approval Form",
        "builder": topic_approval_form,
        "filename": "topic-approval",
    },
    "supervisor_assignment": {
        "label": "Supervisor Assignment Letter",
        "builder": supervisor_assignment_letter,
        "filename": "supervisor-assignment",
    },
    "defense_notice": {
        "label": "Defense Notice",
        "builder": defense_notice,
        "filename": "defense-notice",
    },
    "defense_result": {
        "label": "Defense Result Sheet",
        "builder": defense_result_sheet,
        "filename": "defense-result",
    },
}


def build_form(form_key: str, monograph) -> tuple[bytes, str]:
    """Produce one form, returning its bytes and a sensible filename."""
    spec = AVAILABLE_FORMS.get(form_key)
    if spec is None:
        raise ValueError(f"Unknown form '{form_key}'.")

    pdf = spec["builder"](monograph)
    slug = str(monograph.id)[:8]
    return pdf, f"{spec['filename']}-{slug}.pdf"
