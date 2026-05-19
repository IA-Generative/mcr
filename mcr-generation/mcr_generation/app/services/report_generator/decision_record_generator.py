from mcr_generation.app.schemas.base import DecisionRecord
from mcr_generation.app.services.notes.notes_extractor import ExtractedNotes
from mcr_generation.app.services.report_generator.base_report_generator import (
    BaseReportGenerator,
)
from mcr_generation.app.services.sections.topics.map_reduce_topics import (
    MapReduceTopics,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


class DecisionRecordGenerator(BaseReportGenerator):
    """
    Concrete report generator for decision records.

    Extends `BaseReportGenerator` by implementing the `generate` method to produce
    a `DecisionRecord` report. After extracting the header, it runs a map-reduce
    step over the transcript chunks to identify topics and next steps.
    """

    def generate(
        self,
        chunks: list[Chunk],
        extracted_notes: ExtractedNotes | None = None,
    ) -> DecisionRecord:
        notes = extracted_notes or ExtractedNotes()
        header = self.generate_header(chunks, extracted_notes=extracted_notes)

        map_reduce = MapReduceTopics(
            meeting_subject=header.title,
            participants=header.participants,
        )
        content = map_reduce.map_reduce_all_steps(chunks, notes_hint=notes.topics)

        return DecisionRecord(
            header=header,
            topics_with_decision=content.topics,
            next_steps=content.next_steps,
        )
