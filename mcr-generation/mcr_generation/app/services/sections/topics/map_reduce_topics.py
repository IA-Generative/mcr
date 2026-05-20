"""Map-reduce generator for the Topics section."""

from mcr_generation.app.services.sections.base.map_reduce import BaseMapReduce
from mcr_generation.app.services.sections.topics.prompts import (
    MAP_PROMPT_TEMPLATE,
    REDUCE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.sections.topics.types import (
    MappedTopic,
    MappedTopics,
    TopicsContent,
)


class MapReduceTopics(BaseMapReduce[MappedTopic, TopicsContent]):
    section_name = "topics"
    map_response_model = MappedTopics
    content_model = TopicsContent
    map_prompt_template = MAP_PROMPT_TEMPLATE
    reduce_prompt_template = REDUCE_PROMPT_TEMPLATE
    items_field = "topics"
