from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_docx_loader(monkeypatch: Any) -> MagicMock:  # type: ignore[explicit-any]
    """Monkeypatch UnstructuredWordDocumentLoader; returns the loader class mock."""
    loader_cls = MagicMock()
    monkeypatch.setattr(
        "mcr_generation.app.services.utils.input_chunker.UnstructuredWordDocumentLoader",
        loader_cls,
    )
    return loader_cls
