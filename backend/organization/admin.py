"""Department structure and the rules each department follows."""
from django.contrib import admin

from core.admin import BaseModelAdmin
from organization.models import (
    AcademicYear, Department, DepartmentPolicy, Faculty, ResearchArea, StageDeadline,
)


class DepartmentPolicyInline(admin.StackedInline):
    """
    Edited alongside its department, since a policy has no meaning apart
    from the department it belongs to.
    """

    model = DepartmentPolicy
    can_delete = False
    extra = 0
    fieldsets = (
        ("Approving topics", {
            "fields": ("topic_approval_mode", "topic_approval_votes_required",
                       "supervisor_assignment_mode"),
        }),
        ("Workload", {
            "fields": ("default_max_students_per_supervisor", "allow_group_monographs",
                       "max_students_per_monograph"),
        }),
        ("Defence and grading", {
            "fields": ("committee_size", "supervisor_grade_weight",
                       "committee_grade_weight", "passing_grade"),
        }),
        ("Deadlines and warnings", {
            "fields": ("use_fixed_stage_deadlines", "supervisor_response_days",
                       "student_inactivity_days", "similarity_threshold"),
        }),
    )


@admin.register(Faculty)
class FacultyAdmin(BaseModelAdmin):
    list_display = ("name", "code", "department_count")
    search_fields = ("name", "code")

    @admin.display(description="Departments")
    def department_count(self, obj):
        return obj.departments.count()


@admin.register(Department)
class DepartmentAdmin(BaseModelAdmin):
    list_display = ("name", "code", "faculty", "head", "monograph_count")
    list_filter = ("faculty",)
    search_fields = ("name", "code")
    inlines = [DepartmentPolicyInline]
    autocomplete_fields = ("head",)

    @admin.display(description="Monographs")
    def monograph_count(self, obj):
        return obj.monographs.count()


@admin.register(AcademicYear)
class AcademicYearAdmin(BaseModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current", "is_closed", "monograph_count")
    list_filter = ("is_current", "is_closed")

    @admin.display(description="Monographs")
    def monograph_count(self, obj):
        return obj.monographs.count()


@admin.register(ResearchArea)
class ResearchAreaAdmin(BaseModelAdmin):
    list_display = ("name", "department")
    list_filter = ("department",)
    search_fields = ("name",)


@admin.register(StageDeadline)
class StageDeadlineAdmin(BaseModelAdmin):
    list_display = ("stage", "department", "academic_year", "due_date")
    list_filter = ("department", "academic_year", "stage")
    date_hierarchy = "due_date"
