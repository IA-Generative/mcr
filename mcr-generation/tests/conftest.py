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


def pytest_configure(config):  # noqa: ARG001
    # -- Third-party modules with import-time side effects -------------------
    mock_langfuse = MagicMock()
    mock_langfuse.observe = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules["langfuse"] = mock_langfuse
    sys.modules["openai"] = MagicMock()
    sys.modules["instructor"] = MagicMock()

    # -- Internal utilities that initialise LLM clients at module level ------
    sys.modules["mcr_generation.app.utils.function_execution_timer"] = MagicMock()
    sys.modules["mcr_generation.app.services.utils.llm_helpers"] = MagicMock()

    # -- S3 / storage clients (try to connect at import time) ----------------
    sys.modules["mcr_generation.app.utils.s3_client"] = MagicMock()
    sys.modules["mcr_generation.app.services.utils.s3_service"] = MagicMock()

    # -- Section modules (refiners / map-reduce) -----------------------------
    for _mod in [
        "mcr_generation.app.services.sections",
        "mcr_generation.app.services.sections.intent",
        "mcr_generation.app.services.sections.intent.refine_intent",
        "mcr_generation.app.services.sections.next_meeting",
        "mcr_generation.app.services.sections.next_meeting.refine_next_meeting",
        "mcr_generation.app.services.sections.next_meeting.format_section_for_report",
        "mcr_generation.app.services.sections.participants",
        "mcr_generation.app.services.sections.participants.refine_participants",
        "mcr_generation.app.services.sections.topics",
        "mcr_generation.app.services.sections.topics.map_reduce_topics",
        "mcr_generation.app.services.sections.detailed_discussions",
        "mcr_generation.app.services.sections.detailed_discussions.map_reduce_detailed_discussions",
        "mcr_generation.app.services.sections.discussions_synthesis",
        "mcr_generation.app.services.sections.discussions_synthesis.synthetise_detailed_discussions",
    ]:
        sys.modules[_mod] = MagicMock()
