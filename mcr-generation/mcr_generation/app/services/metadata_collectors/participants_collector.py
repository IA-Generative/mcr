from langfuse import observe

from mcr_generation.app.schemas.base import Participants
from mcr_generation.app.services.metadata_collectors.base import (
    MetadataCollector,
    register,
)
from mcr_generation.app.services.sections.participants.refine_participants import (
    RefineParticipants,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


class ParticipantsCollector(MetadataCollector):
    id = "participants"
    description = (
        "Liste les participants à la réunion avec leur rôle et leur organisation "
        "lorsque ces informations sont mentionnées."
    )

    @observe(name="metadata_collector.participants")
    def _extract(self, chunks: list[Chunk]) -> Participants:
        return RefineParticipants().init_then_refine(chunks)

    def _to_markdown(self, result: Participants) -> str:
        if not result.participants:
            return "_Aucun participant identifié._"
        lines = ["## Participants", ""]
        for p in result.participants:
            label = p.name or p.speaker_id
            role = f" — {p.role}" if p.role else ""
            lines.append(f"- **{label}**{role}")
        return "\n".join(lines)


register(ParticipantsCollector())
