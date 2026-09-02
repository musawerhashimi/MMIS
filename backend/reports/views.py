"""Dashboard and reporting endpoints."""
import csv

from django.http import Http404, HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.enums import FINISHED_STAGES, MonographStage
from core.permissions import IsHeadOfDepartment
from monographs.models import Monograph
from reports.services.dashboards import (
    department_overview,
    stage_breakdown,
    stage_durations,
    student_dashboard,
    supervisor_dashboard,
    supervisor_workload,
)


class DashboardView(APIView):
    """
    One endpoint, shaped to whoever is asking.

    A student, a supervisor and a head of department each need a different
    first screen, so the server decides which one rather than making the
    frontend call three endpoints and discard two.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        department = request.query_params.get("department")
        academic_year = request.query_params.get("academic_year")

        if user.is_student:
            return Response({"role": "student", **student_dashboard(user)})

        if user.is_head_of_department or user.is_admin:
            if not department and user.is_head_of_department:
                first = user.headed_departments.first()
                department = str(first.id) if first else None
            return Response(
                {
                    "role": "head_of_department",
                    **department_overview(user, department, academic_year),
                }
            )

        if user.can_supervise:
            return Response({"role": "supervisor", **supervisor_dashboard(user)})

        # Committee members see what they must examine.
        from defenses.models import Defense
        from defenses.serializers import DefenseSerializer

        defenses = (
            Defense.objects.filter(committee__member=user)
            .select_related("monograph")
            .prefetch_related("committee__member")
            .distinct()
            .order_by("-scheduled_at")
        )
        return Response(
            {
                "role": "committee",
                "assigned_defenses": DefenseSerializer(defenses, many=True).data,
            }
        )


@api_view(["GET"])
@permission_classes([IsHeadOfDepartment])
def workload_report(request):
    """Who is carrying how many students."""
    return Response(
        supervisor_workload(
            request.user,
            request.query_params.get("department"),
            request.query_params.get("academic_year"),
        )
    )


@api_view(["GET"])
@permission_classes([IsHeadOfDepartment])
def bottleneck_report(request):
    """Where monographs spend the most time."""
    queryset = Monograph.objects.visible_to(request.user)
    department = request.query_params.get("department")
    if department:
        queryset = queryset.filter(department_id=department)
    return Response(stage_durations(queryset))


@api_view(["GET"])
@permission_classes([IsHeadOfDepartment])
def progress_report(request):
    """
    The year's progress in one payload.

    This is what the department sends up to the faculty, so it carries both
    the headline numbers and the per-stage detail behind them.
    """
    queryset = Monograph.objects.visible_to(request.user)
    department = request.query_params.get("department")
    academic_year = request.query_params.get("academic_year")
    if department:
        queryset = queryset.filter(department_id=department)
    if academic_year:
        queryset = queryset.filter(academic_year_id=academic_year)

    completed = queryset.filter(stage=MonographStage.COMPLETED)
    grades = [m.final_grade for m in completed if m.final_grade is not None]

    return Response(
        {
            "totals": {
                "total": queryset.count(),
                "active": queryset.exclude(stage__in=FINISHED_STAGES).count(),
                "completed": completed.count(),
            },
            "completion_rate": (
                round(completed.count() / queryset.count() * 100, 1)
                if queryset.count()
                else 0
            ),
            "average_grade": (
                round(sum(grades) / len(grades), 2) if grades else None
            ),
            "by_stage": stage_breakdown(queryset),
        }
    )


@api_view(["GET"])
@permission_classes([IsHeadOfDepartment])
def behind_schedule_report(request):
    """
    Students who have stopped moving.

    Sorted by how long they have been stuck, because that is the order a head
    of department wants to work through them.
    """
    from datetime import timedelta

    from django.utils import timezone

    days = int(request.query_params.get("days", 30))
    cutoff = timezone.now() - timedelta(days=days)

    queryset = (
        Monograph.objects.visible_to(request.user)
        .exclude(stage__in=FINISHED_STAGES)
        .filter(stage_changed_at__lt=cutoff)
        .select_related("supervisor")
        .prefetch_related("members__student")
        .order_by("stage_changed_at")
    )
    department = request.query_params.get("department")
    if department:
        queryset = queryset.filter(department_id=department)

    return Response(
        [
            {
                "id": str(m.id),
                "title": m.title,
                "students": m.student_names,
                "supervisor": m.supervisor.display_name if m.supervisor else None,
                "stage": m.stage,
                "stage_label": m.get_stage_display(),
                "stuck_days": m.days_in_current_stage,
                "progress_percent": m.progress_percent,
            }
            for m in queryset
        ]
    )


@api_view(["GET"])
@permission_classes([IsHeadOfDepartment])
def export_monographs(request):
    """
    The monograph list as a spreadsheet.

    Departments still hand figures to the faculty as files, so this exists to
    stop staff retyping what the system already knows.
    """
    queryset = (
        Monograph.objects.visible_to(request.user)
        .select_related("supervisor", "department", "academic_year", "research_area")
        .prefetch_related("members__student")
    )
    department = request.query_params.get("department")
    academic_year = request.query_params.get("academic_year")
    if department:
        queryset = queryset.filter(department_id=department)
    if academic_year:
        queryset = queryset.filter(academic_year_id=academic_year)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="monographs.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Title",
            "Students",
            "Supervisor",
            "Department",
            "Academic Year",
            "Research Area",
            "Stage",
            "Progress %",
            "Days in Stage",
            "Final Grade",
            "Created",
        ]
    )
    for m in queryset:
        writer.writerow(
            [
                m.title,
                "; ".join(m.student_names),
                m.supervisor.display_name if m.supervisor else "",
                m.department.name,
                m.academic_year.name,
                m.research_area.name if m.research_area else "",
                m.get_stage_display(),
                m.progress_percent,
                m.days_in_current_stage,
                m.final_grade if m.final_grade is not None else "",
                m.created_at.strftime("%Y-%m-%d"),
            ]
        )
    return response


@extend_schema(operation_id="reports_forms_list")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def available_forms(request):
    """
    Which printable forms exist, and which can be produced right now.

    A form is only offered when the information it needs is on record, so
    nobody prints a defense result sheet for a defense that has not happened.
    """
    from reports.services.forms import AVAILABLE_FORMS

    monograph_id = request.query_params.get("monograph")
    monograph = Monograph.objects.filter(pk=monograph_id).first()
    if monograph is None or not monograph.is_visible_to(request.user):
        raise Http404("No such monograph.")

    from core.enums import MonographStage, stage_index

    defense = getattr(monograph, "defense", None)
    readiness = {
        "topic_approval": stage_index(monograph.stage)
        >= stage_index(MonographStage.TOPIC_APPROVED),
        "supervisor_assignment": monograph.supervisor_id is not None,
        "defense_notice": defense is not None and defense.scheduled_at is not None,
        "defense_result": defense is not None and bool(defense.result),
    }

    return Response(
        [
            {
                "key": key,
                "label": spec["label"],
                "available": readiness.get(key, False),
                "url": f"/api/v1/reports/forms/{key}/?monograph={monograph.id}",
            }
            for key, spec in AVAILABLE_FORMS.items()
        ]
    )


@extend_schema(operation_id="reports_forms_print")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def print_form(request, form_key):
    """
    Produce one official form as a PDF.

    Restricted to staff: these carry signature lines and go into the archive,
    so a student should not be able to generate their own approval letter.
    """
    from reports.services.forms import build_form

    monograph_id = request.query_params.get("monograph")
    monograph = (
        Monograph.objects.filter(pk=monograph_id)
        .select_related("department__faculty", "department__head", "supervisor", "academic_year")
        .first()
    )
    if monograph is None or not monograph.is_visible_to(request.user):
        raise Http404("No such monograph.")

    if request.user.is_student:
        return Response(
            {
                "error": {
                    "code": "not_allowed",
                    "message": "Official forms are produced by department staff.",
                    "details": {},
                }
            },
            status=403,
        )

    try:
        pdf, filename = build_form(form_key, monograph)
    except ValueError as exc:
        return Response(
            {"error": {"code": "form_unavailable", "message": str(exc), "details": {}}},
            status=400,
        )

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
