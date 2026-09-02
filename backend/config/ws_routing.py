"""Websocket URL patterns, collected from the apps that push realtime events."""
from django.urls import path

from notifications.consumers import NotificationConsumer
from monographs.consumers import MonographConsumer
from reports.consumers import DashboardConsumer

websocket_urlpatterns = [
    # Per-user stream: notifications, unread counts, personal alerts.
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    # Per-monograph stream: stage changes, new documents, new reviews.
    path("ws/monographs/<uuid:monograph_id>/", MonographConsumer.as_asgi()),
    # Department-wide stream: live dashboard counters for HoD and admin.
    path("ws/dashboard/", DashboardConsumer.as_asgi()),
]
