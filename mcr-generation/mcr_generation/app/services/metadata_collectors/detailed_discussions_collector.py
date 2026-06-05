from langfuse import observe

from mcr_generation.app.services.metadata_collectors.base import (
    MetadataCollector,
    register,
)
from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.sections.detailed_discussions.map_reduce_detailed_discussions import (
    MapReduceDetailedDiscussions,
)
from mcr_generation.app.services.sections.detailed_discussions.types import (
    DiscussionsContent,
)
from mcr_generation.app.services.sections.intent.refine_intent import RefineIntent
from mcr_generation.app.services.sections.participants.refine_participants import (
    RefineParticipants,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


class DetailedDiscussionsCollector(MetadataCollector):
    id = "detailed_discussions"
    description = (
        "Restitue de façon détaillée chaque discussion de la réunion : sujet, "
        "idées clés, décisions, actions à entreprendre et points de vigilance."
    )
    notes_facets = frozenset(
        {NotesFacet.INTENT, NotesFacet.DISCUSSIONS, NotesFacet.PARTICIPANTS}
    )

    @observe(name="metadata_collector.detailed_discussions")
    def _extract(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> DiscussionsContent:
        intent_hint = extracted_notes.intent if extracted_notes is not None else None
        discussions_hint = (
            extracted_notes.discussions if extracted_notes is not None else None
        )
        participants_hint = (
            extracted_notes.participants if extracted_notes is not None else None
        )
        meeting_subject = RefineIntent().init_then_refine(chunks, init_hint=intent_hint)
        participants = (
            RefineParticipants(participants_hint).init_then_refine(chunks).to_public()
        )
        return MapReduceDetailedDiscussions(
            meeting_subject.title, participants.participants
        ).map_reduce_all_steps(chunks, notes_hint=discussions_hint)

    def _to_markdown(self, result: DiscussionsContent) -> str:
        if not result.detailed_discussions:
            return "_Aucune discussion détaillée identifiée._"

        out: list[str] = []
        for d in result.detailed_discussions:
            out.append(f"### {d.title}")
            if d.key_ideas:
                out.append("")
                out.append("**Idées clés**")
                out += [f"- {item}" for item in d.key_ideas]
            if d.decisions:
                out.append("")
                out.append("**Décisions**")
                out += [f"- {item}" for item in d.decisions]
            if d.actions:
                out.append("")
                out.append("**Actions**")
                out += [f"- {item}" for item in d.actions]
            if d.focus_points:
                out.append("")
                out.append("**Points de vigilance**")
                out += [f"- {item}" for item in d.focus_points]
            out.append("")
        return "\n".join(out).rstrip()


register(DetailedDiscussionsCollector())
