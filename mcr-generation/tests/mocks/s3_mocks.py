from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def mock_s3_client(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    """Monkeypatch s3_service.s3_client with a configurable MagicMock."""
    client = MagicMock()
    monkeypatch.setattr(
        "mcr_generation.app.services.utils.s3_service.s3_client",
        client,
    )
    return client


def s3_client_error(code: str) -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": code, "Message": code}},
        operation_name="GetObject",
    )
