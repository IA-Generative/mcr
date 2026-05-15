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
    def generate_header(self, chunks: list[Chunk]) -> Header:
        refine_intent = RefineIntent()
        refine_participants = RefineParticipants()
        refine_next_meeting = RefineNextMeeting()
        intent = refine_intent.init_then_refine(chunks)
        participants = refine_participants.init_then_refine(chunks).to_public()
        next_meeting = refine_next_meeting.init_then_refine(chunks)
        header = Header(
            title=intent.title,
            objective=intent.objective,
            participants=participants.participants,
            next_meeting=format_next_meeting_for_report(next_meeting),
        )
        return header

    @abstractmethod
    def generate(self, chunks: list[Chunk]) -> BaseReport: ...
