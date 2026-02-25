from mcr_generation.app.schemas.base import DecisionRecord, Participants
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

    def generate(self, chunks: list[Chunk]) -> DecisionRecord:
        """
        Generate a decision record report from transcript chunks.

        Extracts the report header, then runs a map-reduce over the chunks to
        identify topics with decisions and next steps.

        Args:
            chunks (list[Chunk]): Ordered list of transcript segments to analyse.

        Returns:
            DecisionRecord: Report containing the header, topics with decisions,
                and next steps.
        """
        header = self.generate_header(chunks)

        map_reduce = MapReduceTopics(
            meeting_subject=header.title,
            speaker_mapping=Participants(participants=header.participants),
        )
        content = map_reduce.map_reduce_all_steps(chunks)

        return DecisionRecord(
            header=header,
            topics_with_decision=content.topics,
            next_steps=content.next_steps,
        )
