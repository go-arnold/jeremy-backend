import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps")


def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = DRFValidationError(detail=exc.messages)

    response = exception_handler(exc, context)

    if response is not None:
        if not isinstance(response.data, dict) or "detail" not in response.data:
            response.data = {"detail": response.data}

        detail = response.data.get("detail")
        if hasattr(detail, "code"):
            response.data["code"] = detail.code

    else:
        logger.exception("Unhandled exception in view", exc_info=exc)
        response = Response(
            {"detail": "Une erreur inattendue est survenue.", "code": "server_error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
