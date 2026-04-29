from typing import Any
from unittest.mock import MagicMock

import pytest

MODULE = "mcr_generation.app.services.report_generation_task_service"


@pytest.fixture
def mock_get_file_from_s3(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    fn = MagicMock()
    monkeypatch.setattr(f"{MODULE}.get_file_from_s3", fn)
    return fn


@pytest.fixture
def mock_chunk_docx_to_document_list(
    monkeypatch: Any,  # type: ignore[explicit-any]
) -> MagicMock:
    fn = MagicMock()
    monkeypatch.setattr(f"{MODULE}.chunk_docx_to_document_list", fn)
    return fn


@pytest.fixture
def mock_get_generator(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    """get_generator returns a generator mock exposing .generate().

    The returned MagicMock is the factory; its .return_value is the generator.
    """
    generator = MagicMock()
    factory = MagicMock(return_value=generator)
    monkeypatch.setattr(f"{MODULE}.get_generator", factory)
    return factory


@pytest.fixture
def mock_httpx_client(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    """Context-manager-capable httpx.Client replacement.

    Returns the client *instance* (already entered). Test code configures
    instance.post.return_value / side_effect directly.
    """
    instance = MagicMock()
    instance.__enter__ = MagicMock(return_value=instance)
    instance.__exit__ = MagicMock(return_value=False)
    client_cls = MagicMock(return_value=instance)
    monkeypatch.setattr(f"{MODULE}.httpx.Client", client_cls)
    instance.cls = client_cls
    return instance


@pytest.fixture
def mock_api_settings(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    settings = MagicMock()
    settings.MCR_CORE_API_URL = "http://mcr-core/api"
    monkeypatch.setattr(f"{MODULE}.api_settings", settings)
    return settings
