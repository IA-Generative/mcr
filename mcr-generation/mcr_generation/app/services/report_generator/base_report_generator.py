from abc import ABC, abstractmethod

from mcr_generation.app.schemas.base import BaseReport, Header
from mcr_generation.app.services.sections.intent.refine_intent import RefineIntent
from mcr_generation.app.services.sections.next_meeting.format_section_for_report import (
    format_next_meeting_for_report,
)
from mcr_generation.app.services.sections.next_meeting.refine_next_meeting import (
    RefineNextMeeting,
)
from mcr_generation.app.services.sections.participants.refine_participants import (
    RefineParticipants,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


class BaseReportGenerator(ABC):
    """
    Abstract base class for report generators.

    Provides the shared logic for extracting the report header (title, objective,
    participants, next meeting) from transcript chunks. Subclasses must implement
    the `generate` method to produce a complete report in the desired format.
    """

    def generate_header(self, chunks: list[Chunk]) -> Header:
        """
        Extract and build the report header from transcript chunks.

        Runs three LLM-based extractors (intent, participants, next meeting) over
        all chunks using an init-then-refine strategy, then assembles the results
        into a `Header` object.

        Args:
            chunks (list[Chunk]): Ordered list of transcript segments to analyse.

        Returns:
            Header: Report header containing the title, objective, participant list,
                and next meeting information.
        """
        refine_intent = RefineIntent()
        refine_participants = RefineParticipants()
        refine_next_meeting = RefineNextMeeting()
        intent = refine_intent.init_then_refine(chunks)
        participants = refine_participants.init_then_refine(chunks)
        next_meeting = refine_next_meeting.init_then_refine(chunks)
        header = Header(
            title=intent.title,
            objective=intent.objective,
            participants=participants.participants,
            next_meeting=format_next_meeting_for_report(next_meeting),
        )
        return header

    @abstractmethod
    def generate(self, chunks: list[Chunk]) -> BaseReport:
        """
        Generate a complete report from transcript chunks.

        Abstract method to be implemented by each subclass according to the
        desired report type (e.g. decision record, detailed synthesis, etc.).

        Args:
            chunks (list[Chunk]): Ordered list of transcript segments to analyse.

        Returns:
            BaseReport: Generated report whose concrete type depends on the implementation.
        """
        ...
