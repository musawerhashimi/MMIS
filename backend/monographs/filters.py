"""Filters for the monograph list."""
import django_filters as filters

from core.enums import FINISHED_STAGES, MonographStage
from monographs.models import Monograph


class MonographFilter(filters.FilterSet):
    stage = filters.MultipleChoiceFilter(choices=MonographStage.choices)
    supervisor = filters.UUIDFilter(field_name="supervisor_id")
    department = filters.UUIDFilter(field_name="department_id")
    academic_year = filters.UUIDFilter(field_name="academic_year_id")
    research_area = filters.UUIDFilter(field_name="research_area_id")

    #: Still in progress, as opposed to completed, rejected or withdrawn.
    active = filters.BooleanFilter(method="filter_active")

    #: Sitting in one stage longer than this many days — the "who is stuck"
    #: question the head of department asks most often.
    stuck_days = filters.NumberFilter(method="filter_stuck")

    unassigned = filters.BooleanFilter(
        field_name="supervisor", lookup_expr="isnull", label="Has no supervisor"
    )

    class Meta:
        model = Monograph
        fields = ["stage", "supervisor", "department", "academic_year", "research_area"]

    def filter_active(self, queryset, name, value):
        if value is True:
            return queryset.exclude(stage__in=FINISHED_STAGES)
        if value is False:
            return queryset.filter(stage__in=FINISHED_STAGES)
        return queryset

    def filter_stuck(self, queryset, name, value):
        from datetime import timedelta

        from django.utils import timezone

        if value in (None, ""):
            return queryset
        cutoff = timezone.now() - timedelta(days=float(value))
        return queryset.filter(stage_changed_at__lt=cutoff).exclude(
            stage__in=FINISHED_STAGES
        )
