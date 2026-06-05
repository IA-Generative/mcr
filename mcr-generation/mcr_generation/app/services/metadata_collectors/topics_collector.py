from langfuse import observe

from mcr_generation.app.services.metadata_collectors.base import (
    MetadataCollector,
    register,
)
from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.sections.intent.refine_intent import RefineIntent
from mcr_generation.app.services.sections.participants.refine_participants import (
    RefineParticipants,
)
from mcr_generation.app.services.sections.topics.map_reduce_topics import (
    MapReduceTopics,
)
from mcr_generation.app.services.sections.topics.types import TopicsContent
from mcr_generation.app.services.utils.input_chunker import Chunk


class TopicsCollector(MetadataCollector):
    id = "topics"
    description = (
        "Extrait les sujets de discussion principaux et leurs décisions associées, "
        "ainsi que la liste des prochaines étapes (next steps) identifiées."
    )
    notes_facets = frozenset(
        {NotesFacet.INTENT, NotesFacet.TOPICS, NotesFacet.PARTICIPANTS}
    )

    @observe(name="metadata_collector.topics")
    def _extract(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> TopicsContent:
        intent_hint = extracted_notes.intent if extracted_notes is not None else None
        topics_hint = extracted_notes.topics if extracted_notes is not None else None
        participants_hint = (
            extracted_notes.participants if extracted_notes is not None else None
        )
        meeting_subject = RefineIntent().init_then_refine(chunks, init_hint=intent_hint)
        participants = (
            RefineParticipants(participants_hint).init_then_refine(chunks).to_public()
        )
        return MapReduceTopics(
            meeting_subject.title, participants.participants
        ).map_reduce_all_steps(chunks, notes_hint=topics_hint)

    def _to_markdown(self, result: TopicsContent) -> str:
        out: list[str] = []
        if result.topics:
            out.append("### Sujets et décisions")
            out.append("")
            for t in result.topics:
                out.append(f"#### {t.title}")
                if t.introduction_text:
                    out.append("")
                    out.append(t.introduction_text)
                for detail in t.details:
                    out.append(f"- {detail}")
                if t.main_decision:
                    out.append("")
                    out.append(f"**Décision** : {t.main_decision}")
                out.append("")
        if result.next_steps:
            out.append("### Prochaines étapes")
            out.append("")
            for s in result.next_steps:
                out.append(f"- {s}")
        return "\n".join(out).rstrip() or "_Aucun sujet ni étape identifiés._"


register(TopicsCollector())
