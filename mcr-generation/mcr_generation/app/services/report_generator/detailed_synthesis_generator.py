from mcr_generation.app.schemas.base import DetailedSynthesis, Participants
from mcr_generation.app.services.report_generator.base_report_generator import (
    BaseReportGenerator,
)
from mcr_generation.app.services.sections.detailed_discussions.map_reduce_detailed_discussions import (
    MapReduceDetailedDiscussions,
)
from mcr_generation.app.services.utils.input_chunker import Chunk


class DetailedSynthesisGenerator(BaseReportGenerator):
    """
    Concrete report generator for detailed syntheses.

    Extends `BaseReportGenerator` by implementing the `generate` method to produce
    a `DetailedSynthesis` report. After extracting the header, it populates the
    various synthesis sections (discussions summary, detailed discussions, to-do
    list, and items to monitor).

    see outtput example in: report_generator/examples/detailed_synthesis_example.json
    """

    def generate(self, chunks: list[Chunk]) -> DetailedSynthesis:
        header = self.generate_header(chunks)

        map_reduce = MapReduceDetailedDiscussions(
            meeting_subject=header.title,
            speaker_mapping=Participants(participants=header.participants),
        )
        content = map_reduce.map_reduce_all_steps(chunks)

        return DetailedSynthesis(
            header=header,
            discussions_summary=[],
            detailed_discussions=content.detailed_discussions,
            to_do_list=[],
            to_monitor_list=[],
        )
