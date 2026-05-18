from abc import ABC, abstractmethod

from mcr_generation.app.schemas.base import BaseReport, Header
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
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

    def generate_header(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> Header:
        """
        Extract and build the report header from transcript chunks.

        Runs three LLM-based extractors (intent, participants, next meeting) over
        all chunks using an init-then-refine strategy, then assembles the results
        into a `Header` object. When `extracted_notes` is provided, the `intent`
        and `next_meeting` fields are used as seeds for their respective refiners,
        skipping the initial LLM extract and refining every chunk against the seed.

        Args:
            chunks (list[Chunk]): Ordered list of transcript segments to analyse.
            extracted_notes (ExtractedNotes | None): Structured hints extracted by
                `NotesExtractor` from user-written meeting notes. When provided,
                its `intent` and `next_meeting` fields seed the corresponding
                refiners.

        Returns:
            Header: Report header containing the title, objective, participant list,
                and next meeting information.
        """
        notes = extracted_notes or ExtractedNotes()
        refine_intent = RefineIntent()
        refine_participants = RefineParticipants()
        refine_next_meeting = RefineNextMeeting()
        intent = refine_intent.init_then_refine(chunks, init_hint=notes.intent)
        participants = refine_participants.init_then_refine(chunks).to_public()
        next_meeting = refine_next_meeting.init_then_refine(
            chunks, init_hint=notes.next_meeting
        )
        header = Header(
            title=intent.title,
            objective=intent.objective,
            participants=participants.participants,
            next_meeting=format_next_meeting_for_report(next_meeting),
        )
        return header

    @abstractmethod
    def generate(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> BaseReport:
        """
        Generate a complete report from transcript chunks.

        Abstract method to be implemented by each subclass according to the
        desired report type (e.g. decision record, detailed synthesis, etc.).

        Args:
            chunks (list[Chunk]): Ordered list of transcript segments to analyse.
            extracted_notes (ExtractedNotes | None): Structured hints extracted by
                `NotesExtractor` from user-written meeting notes. Forwarded to
                `generate_header` to seed the relevant refiners.

        Returns:
            BaseReport: Generated report whose concrete type depends on the implementation.
        """
        ...
