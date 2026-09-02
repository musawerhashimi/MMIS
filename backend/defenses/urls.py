from rest_framework.routers import DefaultRouter

from defenses.views import DefenseViewSet

app_name = "defenses"

router = DefaultRouter()
router.register("", DefenseViewSet, basename="defense")

urlpatterns = router.urls
