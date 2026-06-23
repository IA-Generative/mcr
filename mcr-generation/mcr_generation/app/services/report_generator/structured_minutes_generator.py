from typing import ClassVar

from mcr_generation.app.schemas.base import StructuredMinutes
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.report_generator.base_report_generator import (
    BaseReportGenerator,
)
from mcr_generation.app.services.sections.minutes_synthesis.minutes_synthesizer import (
    MinutesSynthesizer,
)
from mcr_generation.app.services.sections.structured_minutes.map_reduce_minutes import (
    MapReduceMinutes,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


class StructuredMinutesGenerator(BaseReportGenerator):
    """
    Générateur du compte-rendu structuré (STRUCTURED_MINUTES).

    Après extraction du header, lance un map-reduce des thématiques et de leurs
    décisions, puis un synthétiseur qui produit les points en suspens et les
    recommandations.
    """

    report_type: ClassVar[ReportTypes] = ReportTypes.STRUCTURED_MINUTES

    def generate(
        self,
        chunks: list[Chunk],
        notes_content: str | None = None,
    ) -> StructuredMinutes:
        extracted_notes = self._extract_notes(notes_content)
        header = self.generate_header(chunks, extracted_notes=extracted_notes)

        content = MapReduceMinutes(
            meeting_subject=header.title,
            participants=header.participants,
        ).map_reduce_all_steps(chunks)

        synth = MinutesSynthesizer(
            meeting_subject=header.title,
            participants=header.participants,
        ).synthesize(content.themes)

        return StructuredMinutes(
            header=header,
            themes=content.themes,
            open_points=synth.open_points,
            recommendations=synth.recommendations,
        )
