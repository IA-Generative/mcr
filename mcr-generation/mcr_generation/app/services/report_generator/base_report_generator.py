import asyncio
from abc import ABC, abstractmethod
from typing import ClassVar

from loguru import logger

from mcr_generation.app.schemas.base import BaseReport, Header
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.notes.facets import facets_for_report_type
from mcr_generation.app.services.notes.notes_extractor import (
    ExtractedNotes,
    NotesExtractor,
)
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

    Subclasses declare `report_type` so that `_extract_notes` can look up the
    relevant set of notes facets from `facets_for_report_type`.
    """

    report_type: ClassVar[ReportTypes]

    def _extract_notes(self, notes_content: str | None) -> ExtractedNotes | None:
        """Extract structured notes hints from user-written content.

        Returns `None` when there is nothing to extract (no content, blank
        content, or no facets configured for this report type) — no LLM call
        is made in those cases.
        """
        if not notes_content or not notes_content.strip():
            logger.debug("Notes extraction skipped: no notes content")
            return None

        facets = facets_for_report_type(self.report_type)
        if not facets:
            logger.debug(
                "Notes extraction skipped: no facets for report_type {}",
                self.report_type,
            )
            return None

        extracted_notes = asyncio.run(
            NotesExtractor().extract_all(notes_content, facets=facets)
        )
        logger.debug("Notes extraction done")
        return extracted_notes

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
        and `next_meeting` fields are used as seeds for their respective refiners
        (skipping the initial LLM extract), while the `participants` field is
        injected as a read-only reference hint into the participant prompts to
        help name/qualify detected speakers (never as a seed).

        Args:
            chunks (list[Chunk]): Ordered list of transcript segments to analyse.
            extracted_notes (ExtractedNotes | None): Structured hints extracted by
                `NotesExtractor` from user-written meeting notes. When provided,
                its `intent` and `next_meeting` fields seed the corresponding
                refiners and its `participants` field is passed as a notes hint to
                the participant refiner.

        Returns:
            Header: Report header containing the title, objective, participant list,
                and next meeting information.
        """
        notes = extracted_notes or ExtractedNotes()
        refine_intent = RefineIntent()
        refine_participants = RefineParticipants(notes.participants)
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
        notes_content: str | None = None,
    ) -> BaseReport:
        """
        Generate a complete report from transcript chunks.

        Abstract method implemented by each subclass according to the desired
        report type. Implementations are expected to call `self._extract_notes`
        on `notes_content` before invoking `generate_header` and the
        section-specific pipelines, so notes hints can seed the relevant
        refiners and map-reduce reduce steps.

        Args:
            chunks (list[Chunk]): Ordered list of transcript segments to analyse.
            notes_content (str | None): Raw user-written meeting notes. May be
                `None` or blank, in which case no notes extraction occurs.

        Returns:
            BaseReport: Generated report whose concrete type depends on the implementation.
        """
        ...
