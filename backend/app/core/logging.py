"""Privacy-safe structured access logging.

Emits one JSON line per request with request id, method, path, status and
duration. It deliberately never records the Authorization header, request or
response bodies, ciphertext, query strings, or the Telegram id — only the URL
path (which carries no PII in this API).
"""

import json
import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
_LOGGED_FIELDS = ("request_id", "method", "path", "status", "duration_ms")

access_logger = logging.getLogger("app.access")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {"event": record.getMessage()}
        for field in _LOGGED_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    app_logger = logging.getLogger("app")
    app_logger.handlers = [handler]
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
        started_at = time.perf_counter()

        response = await call_next(request)

        access_logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
