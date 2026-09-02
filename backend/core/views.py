"""
Health endpoints.

The university server is expected to run without a sysadmin watching it, so
these give a plain answer to "is it working" and "why not".
"""
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness: the process is up and serving."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class ReadinessView(APIView):
    """Readiness: the things this app depends on are reachable."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        checks = {}

        try:
            connection.ensure_connection()
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001 - report, don't crash the probe
            checks["database"] = f"error: {exc.__class__.__name__}"

        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            layer = get_channel_layer()
            async_to_sync(layer.send)("health-probe", {"type": "ping"})
            checks["realtime"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["realtime"] = f"error: {exc.__class__.__name__}"

        healthy = all(v == "ok" for v in checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
