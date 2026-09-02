from django.urls import path

from reports.views import (
    DashboardView,
    available_forms,
    behind_schedule_report,
    bottleneck_report,
    export_monographs,
    print_form,
    progress_report,
    workload_report,
)

app_name = "reports"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("workload/", workload_report, name="workload"),
    path("bottlenecks/", bottleneck_report, name="bottlenecks"),
    path("progress/", progress_report, name="progress"),
    path("behind-schedule/", behind_schedule_report, name="behind-schedule"),
    path("export/monographs/", export_monographs, name="export-monographs"),
    path("forms/", available_forms, name="available-forms"),
    path("forms/<str:form_key>/", print_form, name="print-form"),
]
