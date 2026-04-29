from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_instructor_client() -> MagicMock:
    """Pre-wired Instructor client — chat.completions.create is a MagicMock."""
    client = MagicMock()
    client.chat.completions.create = MagicMock()
    return client
