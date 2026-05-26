from langfuse import observe

from mcr_generation.app.schemas.base import Intent
from mcr_generation.app.services.metadata_collectors.base import (
    MetadataCollector,
    register,
)
from mcr_generation.app.services.notes.facets import NotesFacet
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.sections.intent.refine_intent import RefineIntent
from mcr_generation.app.services.utils.input_chunker import Chunk


class TitleCollector(MetadataCollector):
    id = "title"
    description = (
        "Fournit le titre court de la réunion et son objectif principal en une "
        "phrase concise."
    )
    notes_facets = frozenset({NotesFacet.INTENT})

    @observe(name="metadata_collector.title")
    def _extract(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> Intent:
        init_hint = extracted_notes.intent if extracted_notes is not None else None
        return RefineIntent().init_then_refine(chunks, init_hint=init_hint)

    def _to_markdown(self, result: Intent) -> str:
        title = result.title or "_Titre non identifié_"
        out = [f"**{title}**"]
        if result.objective:
            out += ["", f"_Objectif : {result.objective}_"]
        return "\n".join(out)


register(TitleCollector())
