"""
Global test configuration for mcr-generation.

pytest_configure runs before any test module is imported, so sys.modules
entries set here are guaranteed to be in place when each test file is
collected and its top-level imports are executed.

Only modules that have side effects at import time are listed here
(network calls, LLM client initialisation, Langfuse telemetry, …).
Modules that are the actual subject under test are NOT mocked here —
each test file imports its own module under test after this setup runs.
"""

import sys
from unittest.mock import MagicMock

from tests.mocks.docx_mocks import mock_docx_loader  # noqa: F401
from tests.mocks.llm_mocks import (  # noqa: F401
    fake_async_call_llm_with_structured_output,
    fake_call_llm_with_structured_output,
    mock_instructor_client,
)
from tests.mocks.s3_mocks import mock_s3_client  # noqa: F401
from tests.mocks.task_service_mocks import (  # noqa: F401
    mock_chunk_docx_to_document_list,
    mock_core_api_client,
    mock_create_report_generator,
    mock_get_file_from_s3,
)


def pytest_configure(config):  # noqa: ARG001
    # -- Third-party modules with import-time side effects -------------------
    mock_langfuse = MagicMock()
    mock_langfuse.observe = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules["langfuse"] = mock_langfuse
    sys.modules["openai"] = MagicMock()
    sys.modules["instructor"] = MagicMock()

    # -- S3 client: calls boto3.client() at import time with live env vars ---
    sys.modules["mcr_generation.app.utils.s3_client"] = MagicMock()

    # -- Pre-load real Pydantic type modules ---------------------------------
    # The metadata collectors import their `*Content` Pydantic types from these
    # submodules. Loading them BEFORE the mocking loop below ensures
    # `sys.modules` already holds the real modules, so `from <parent>.types
    # import <Name>Content` resolves directly without traversing the (mocked)
    # parent package.
    # These modules are pure Pydantic schemas — no LLM client init.
    import mcr_generation.app.services.sections.detailed_discussions.types  # noqa: F401
    import mcr_generation.app.services.sections.topics.types  # noqa: F401

    # -- Section modules (refiners / map-reduce) -----------------------------
    # Note: only leaf modules that would trigger real LLM client initialisation
    # are mocked here.  Parent packages are NOT mocked so that importlib can
    # resolve sibling sub-modules (e.g. `topics.types`, which holds pure
    # Pydantic schemas needed by `notes_extractor`) from the real filesystem
    # __path__.  The sections/__init__.py imports succeed because every leaf
    # it references is already stubbed out below.
    for _mod in [
        "mcr_generation.app.services.sections.intent.refine_intent",
        "mcr_generation.app.services.sections.next_meeting.refine_next_meeting",
        "mcr_generation.app.services.sections.next_meeting.format_section_for_report",
        "mcr_generation.app.services.sections.participants.refine_participants",
        "mcr_generation.app.services.sections.topics.map_reduce_topics",
        "mcr_generation.app.services.sections.detailed_discussions.map_reduce_detailed_discussions",
    ]:
        sys.modules[_mod] = MagicMock()
