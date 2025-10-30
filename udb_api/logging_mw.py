"""Logging & correlation ID middleware."""
from __future__ import annotations
import time
import uuid
import logging
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("udb")

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):  # type: ignore
        start = time.time()
        cid = request.headers.get("x-correlation-id", uuid.uuid4().hex)
        request.state.correlation_id = cid
        logger.info({"event": "request_start", "path": request.url.path, "cid": cid})
        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover
            logger.exception("request_error", extra={"cid": cid})
            raise exc
        duration = time.time() - start
        response.headers["x-correlation-id"] = cid
        logger.info({"event": "request_end", "path": request.url.path, "cid": cid, "duration_ms": int(duration*1000)})
        return response
