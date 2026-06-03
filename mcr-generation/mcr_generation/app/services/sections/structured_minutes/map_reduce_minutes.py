"""Map-reduce generator for the structured minutes section."""

from mcr_generation.app.services.sections.base.map_reduce import BaseMapReduce
from mcr_generation.app.services.sections.structured_minutes.prompts import (
    MAP_PROMPT_TEMPLATE,
    REDUCE_PROMPT_TEMPLATE,
)
from mcr_generation.app.services.sections.structured_minutes.types import (
    MappedMinutesLLM,
    MappedMinuteTheme,
    MinutesContent,
)


class MapReduceMinutes(BaseMapReduce[MappedMinuteTheme, MinutesContent]):
    section_name = "structured_minutes"
    map_response_model = MappedMinutesLLM
    item_model = MappedMinuteTheme
    content_model = MinutesContent
    map_prompt_template = MAP_PROMPT_TEMPLATE
    reduce_prompt_template = REDUCE_PROMPT_TEMPLATE
    items_field = "themes"
