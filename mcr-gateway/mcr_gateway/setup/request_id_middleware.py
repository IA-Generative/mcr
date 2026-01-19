import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class AddRequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
            logger.info("{} {} {}", request.method, request.url, response.status_code)
        return response
