from fastapi import FastAPI
from pytest_httpx import HTTPXMock
from starlette.testclient import TestClient

from mcr_gateway.app.utils.core_http_client import core_client
from mcr_gateway.setup.request_id_middleware import (
    REQUEST_ID_HEADER,
    AddRequestIdMiddleware,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AddRequestIdMiddleware)

    @app.get("/proxy")
    async def proxy() -> dict[str, int]:
        async with core_client(base_url="http://core.test") as client:
            response = await client.get("/downstream")
        return {"status": response.status_code}

    return app


def test_forwards_the_request_id_to_core(httpx_mock: HTTPXMock) -> None:
    # The id the gateway assigned to the inbound request must ride along on the
    # call it makes to core, so both services log the same id for one request.
    httpx_mock.add_response(url="http://core.test/downstream")
    client = TestClient(_build_app())

    client.get("/proxy", headers={REQUEST_ID_HEADER: "req-xyz"})

    outbound = httpx_mock.get_requests()[0]
    assert outbound.headers.get(REQUEST_ID_HEADER) == "req-xyz"
