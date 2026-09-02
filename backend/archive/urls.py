from rest_framework.routers import DefaultRouter

from archive.views import ArchiveViewSet, SimilarityViewSet

app_name = "archive"

router = DefaultRouter()
router.register("similarities", SimilarityViewSet, basename="similarity")
router.register("", ArchiveViewSet, basename="archive")

urlpatterns = router.urls
