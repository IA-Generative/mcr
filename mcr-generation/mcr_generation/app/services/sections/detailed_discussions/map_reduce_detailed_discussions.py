"""Map-reduce generator for the Detailed Discussions section."""

from mcr_generation.app.services.sections.base.map_reduce import BaseMapReduce
from mcr_generation.app.services.sections.detailed_discussions.prompts import (
    MAP_PROMPT_TEMPLATE,
    REDUCE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.sections.detailed_discussions.types import (
    DiscussionsContent,
    MappedDetailedDiscussion,
    MappedDetailedDiscussionsLLM,
)


class MapReduceDetailedDiscussions(
    BaseMapReduce[MappedDetailedDiscussion, DiscussionsContent]
):
    section_name = "detailed_discussions"
    map_response_model = MappedDetailedDiscussionsLLM
    item_model = MappedDetailedDiscussion
    content_model = DiscussionsContent
    map_prompt_template = MAP_PROMPT_TEMPLATE
    reduce_prompt_template = REDUCE_PROMPT_TEMPLATE
    items_field = "detailed_discussions"
