import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "X-Request-ID"


class AddRequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Adopt the gateway's id when it forwards one so both services log the
        # same id for a single request; mint one otherwise (direct/internal call).
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
            logger.info("{} {} {}", request.method, request.url, response.status_code)
        return response
