from django.urls import path

from core.views import HealthView, ReadinessView

urlpatterns = [
    path("", HealthView.as_view(), name="health"),
    path("ready/", ReadinessView.as_view(), name="readiness"),
]
