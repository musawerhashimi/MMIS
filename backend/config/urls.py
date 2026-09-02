"""
Root URL configuration.

Everything the SPA talks to lives under /api/v1/. The Django admin is kept
for the system administrator, and the OpenAPI schema is exposed in non-prod
so the frontend can generate types from it.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# Branding for the administrator's own screens.
admin.site.site_header = "Monograph Management"
admin.site.site_title = "Monograph Management"
admin.site.index_title = "System administration"

api_v1 = [
    path("auth/", include("accounts.urls")),
    path("organization/", include("organization.urls")),
    path("monographs/", include("monographs.urls")),
    path("documents/", include("documents.urls")),
    path("reviews/", include("reviews.urls")),
    path("defenses/", include("defenses.urls")),
    path("notifications/", include("notifications.urls")),
    path("reports/", include("reports.urls")),
    path("archive/", include("archive.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/health/", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
