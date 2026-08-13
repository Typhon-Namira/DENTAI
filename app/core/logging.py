import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request
from starlette.responses import Response

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )


async def request_logging(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        status_code = getattr(locals().get("response"), "status_code", 500)
        structlog.get_logger().info(
            "request",
            request_id=request_id,
            method=request.method,
            route=request.url.path,
            status_code=status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        if "response" in locals():
            response.headers["x-request-id"] = request_id


async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
