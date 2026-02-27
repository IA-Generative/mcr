from unittest.mock import patch

import pytest

from mcr_generation.app.schemas.base import DetailedDiscussion
from mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer import (
    DetailedDiscussionsSynthesizer,
)
from mcr_generation.app.services.sections.discussions_synthesis.types import Content


@pytest.fixture
def mock_detailed_discussions():
    return [
        DetailedDiscussion(
            title="Discussion 1",
            key_ideas=["Idea 1"],
            decisions=["Decision 1"],
            actions=["Action 1"],
            focus_points=["Focus 1"],
        ),
        DetailedDiscussion(
            title="Discussion 2",
            key_ideas=["Idea 2"],
            decisions=["Decision 2"],
            actions=["Action 2"],
            focus_points=["Focus 2"],
        ),
    ]


class TestSynthesizeDetailedDiscussions:
    def test_synthesize_detailed_discussions_empty_list(self) -> None:
        """Test synthesize_detailed_discussions with an empty list of discussions."""
        detailed_discussions_synthesizer = DetailedDiscussionsSynthesizer(
            meeting_subject="Subject",
            participants=[],
        )
        result = detailed_discussions_synthesizer.synthesize(detailed_discussions=[])
        assert isinstance(result, Content)
        assert result.discussions_summary == []
        assert result.to_do_list == []
        assert result.to_monitor_list == []

    @patch(
        "mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer.call_llm_with_structured_output"
    )
    @patch(
        "mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer.LLMConfig"
    )
    @patch(
        "mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer.OpenAI"
    )
    @patch(
        "mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer.instructor"
    )
    def test_synthesize_detailed_discussions_calls_llm(
        self,
        mock_instructor,
        mock_openai,
        mock_llm_config,
        mock_call_llm,
        mock_detailed_discussions,
    ) -> None:
        """Test synthesize_detailed_discussions calls the LLM with correct parameters."""
        expected_content = Content(
            discussions_summary=["Summary 1"],
            to_do_list=["Action A"],
            to_monitor_list=["Point Z"],
        )
        mock_call_llm.return_value = expected_content

        meeting_subject = "Important Meeting"
        speaker_mapping = "Speaker 1: Alice"

        # Run function

        detailed_discussions_synthesizer = DetailedDiscussionsSynthesizer(
            meeting_subject=meeting_subject,
            participants=speaker_mapping,
        )
        result = detailed_discussions_synthesizer.synthesize(
            detailed_discussions=mock_detailed_discussions,
        )

        # Assertions
        assert result == expected_content
        mock_call_llm.assert_called_once()

        # Verify prompt content
        _, kwargs = mock_call_llm.call_args
        user_message_content = kwargs["user_message_content"]
        assert meeting_subject in user_message_content
        assert speaker_mapping in user_message_content

        # Check if discussions are in the prompt
        for disc in mock_detailed_discussions:
            assert disc.title in user_message_content

    @patch(
        "mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer.call_llm_with_structured_output"
    )
    @patch(
        "mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer.LLMConfig"
    )
    @patch(
        "mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer.OpenAI"
    )
    @patch(
        "mcr_generation.app.services.sections.discussions_synthesis.detailed_discussions_synthesizer.instructor"
    )
    def test_synthesize_detailed_discussions_none_parameters(
        self,
        mock_instructor,
        mock_openai,
        mock_llm_config,
        mock_call_llm,
    ) -> None:
        """Test synthesize_detailed_discussions with None for subject and mapping."""
        mock_call_llm.return_value = Content()

        detailed_discussions_synthesizer = DetailedDiscussionsSynthesizer(
            meeting_subject=None,
            participants=[],
        )
        _result = detailed_discussions_synthesizer.synthesize(
            detailed_discussions=[
                DetailedDiscussion(
                    title="T", key_ideas=[], decisions=[], actions=[], focus_points=[]
                )
            ],
        )

        _, kwargs = mock_call_llm.call_args
        user_message_content = kwargs["user_message_content"]
        assert "Objet de la réunion : Inconnu" in user_message_content
        assert (
            "Mapping entre les interlocuteurs et leurs noms/rôles si disponible : Non fourni"
            in user_message_content
        )
