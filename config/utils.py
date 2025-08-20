from typing import Any, Dict, Optional

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc: Exception, context: Dict[str, Any]) -> Optional[Response]:
    response = drf_exception_handler(exc, context)
    request: Request = context.get("request")  # type: ignore
    request_id = request.headers.get("X-Request-ID") if request else None
    if response is None:
        body = {
            "error": {"code": "server_error", "message": "Internal server error"},
            "request_id": request_id,
        }
        return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if response.status_code >= 400:
        data = response.data
        code = (
            getattr(getattr(exc, "default_code", ""), "code", "")
            or (data.get("code") if isinstance(data, dict) else None)
            or "error"
        )
        message = data.get("detail") if isinstance(data, dict) else str(data)
        response.data = {
            "error": {"code": code, "message": message},
            "request_id": request_id,
        }
    return response
