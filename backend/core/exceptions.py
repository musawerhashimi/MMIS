"""
One consistent error shape for the whole API.

The frontend has a single error handler, so every failure — validation,
permission, workflow rule — arrives looking the same:

    {"error": {"code": "...", "message": "...", "details": {...}}}
"""
import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class DomainError(exceptions.APIException):
    """
    A business rule was broken.

    Raised by the service layer — for example trying to move a monograph to a
    stage it cannot legally reach from where it is now.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This action is not allowed."
    default_code = "domain_error"

    def __init__(self, detail=None, code=None, details=None):
        super().__init__(detail, code)
        self.details = details or {}


class InvalidStageTransition(DomainError):
    default_detail = "This monograph cannot move to that stage from its current stage."
    default_code = "invalid_stage_transition"


class WorkflowPermissionDenied(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Your role does not allow this action on this monograph."
    default_code = "workflow_permission_denied"


def api_exception_handler(exc, context):
    """Normalise every exception into the shared envelope."""
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)

    if response is None:
        # Genuinely unexpected — log it with the request for debugging.
        request = context.get("request")
        logger.exception("Unhandled error on %s", getattr(request, "path", "?"))
        return Response(
            {
                "error": {
                    "code": "server_error",
                    "message": "Something went wrong. Please try again.",
                    "details": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    code = getattr(exc, "default_code", "error")
    details = getattr(exc, "details", {})

    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
    elif isinstance(detail, dict):
        # Field validation errors: keep them keyed by field for the form UI.
        message = "Please correct the highlighted fields."
        details = detail
    elif isinstance(detail, list):
        message = str(detail[0]) if detail else "Request failed."
    else:
        message = str(detail)

    response.data = {
        "error": {"code": code, "message": message, "details": details}
    }
    return response
