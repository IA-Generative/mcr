from langfuse import observe

from mcr_generation.app.schemas.base import NextMeeting
from mcr_generation.app.services.metadata_collectors.base import (
    MetadataCollector,
    register,
)
from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.sections.next_meeting.format_section_for_report import (
    format_next_meeting_for_report,
)
from mcr_generation.app.services.sections.next_meeting.refine_next_meeting import (
    RefineNextMeeting,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


class NextMeetingCollector(MetadataCollector):
    id = "next_meeting"
    description = (
        "Décrit la prochaine réunion mentionnée (objet, date, heure) si elle est "
        "explicite ou raisonnablement déductible de la transcription."
    )
    notes_facets = frozenset({NotesFacet.NEXT_MEETING})

    @observe(name="metadata_collector.next_meeting")
    def _extract(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> NextMeeting:
        init_hint = (
            extracted_notes.next_meeting if extracted_notes is not None else None
        )
        return RefineNextMeeting().init_then_refine(chunks, init_hint=init_hint)

    def _to_markdown(self, result: NextMeeting) -> str:
        formatted = format_next_meeting_for_report(result)
        if formatted is None:
            return "_Pas de prochaine réunion mentionnée._"
        return formatted


register(NextMeetingCollector())
