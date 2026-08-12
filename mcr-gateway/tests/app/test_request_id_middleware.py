from fastapi import FastAPI
from starlette.testclient import TestClient

from mcr_gateway.setup.request_id_middleware import (
    REQUEST_ID_HEADER,
    AddRequestIdMiddleware,
    get_request_id,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AddRequestIdMiddleware)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        # Surface the id the middleware bound so we can assert it is in scope.
        return {"request_id": get_request_id()}

    return app


def test_generates_a_request_id_and_echoes_it_on_the_response() -> None:
    client = TestClient(_build_app())

    response = client.get("/ping")

    echoed = response.headers.get(REQUEST_ID_HEADER)
    assert echoed
    assert response.json()["request_id"] == echoed


def test_honors_an_incoming_request_id() -> None:
    client = TestClient(_build_app())

    response = client.get("/ping", headers={REQUEST_ID_HEADER: "upstream-42"})

    assert response.headers.get(REQUEST_ID_HEADER) == "upstream-42"
    assert response.json()["request_id"] == "upstream-42"
