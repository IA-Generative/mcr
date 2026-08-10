import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from mcr_gateway.setup.sentry import tag_request_id

REQUEST_ID_HEADER = "X-Request-ID"

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_ctx.get()


class AddRequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Adopt an upstream id when present so a request keeps one id end to end.
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = _request_id_ctx.set(request_id)
        tag_request_id(request_id)
        try:
            with logger.contextualize(request_id=request_id):
                response = await call_next(request)
                logger.info(
                    "{} {} {}", request.method, request.url, response.status_code
                )
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            _request_id_ctx.reset(token)
