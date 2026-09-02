from rest_framework.routers import DefaultRouter

from organization.views import (
    AcademicYearViewSet,
    ChoicesView,
    DepartmentViewSet,
    FacultyViewSet,
    ResearchAreaViewSet,
    StageDeadlineViewSet,
)

app_name = "organization"

router = DefaultRouter()
router.register("faculties", FacultyViewSet, basename="faculty")
router.register("departments", DepartmentViewSet, basename="department")
router.register("academic-years", AcademicYearViewSet, basename="academic-year")
router.register("research-areas", ResearchAreaViewSet, basename="research-area")
router.register("stage-deadlines", StageDeadlineViewSet, basename="stage-deadline")
router.register("choices", ChoicesView, basename="choices")

urlpatterns = router.urls
