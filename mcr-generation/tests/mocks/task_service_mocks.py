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
def mock_core_api_client(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    """Replaces CoreApiClient at the service module's import site.

    Tests assert against the returned instance's mark_* methods.
    """
    instance = MagicMock()
    cls = MagicMock(return_value=instance)
    monkeypatch.setattr(f"{MODULE}.CoreApiClient", cls)
    instance.cls = cls
    return instance
