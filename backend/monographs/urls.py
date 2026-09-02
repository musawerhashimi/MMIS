from rest_framework.routers import DefaultRouter

from monographs.views import MonographViewSet

app_name = "monographs"

router = DefaultRouter()
router.register("", MonographViewSet, basename="monograph")

urlpatterns = router.urls
