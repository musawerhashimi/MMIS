from django.urls import include, path
from rest_framework.routers import DefaultRouter

from documents.views import DocumentViewSet, DownloadView, UploadView

app_name = "documents"

router = DefaultRouter()
router.register("", DocumentViewSet, basename="document")

urlpatterns = [
    path("upload/", UploadView.as_view(), name="upload"),
    path("versions/<uuid:version_id>/download/", DownloadView.as_view(), name="download"),
    path("", include(router.urls)),
]
