from mcr_generation.app.schemas.base import ParticipantsWithThinkingListWrapper
from mcr_generation.app.services.sections.base.init_then_refine import (
    BaseInitThenRefine,
)
from mcr_generation.app.services.sections.participants.prompts import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
)


class RefineParticipants(BaseInitThenRefine[ParticipantsWithThinkingListWrapper]):
    response_model = ParticipantsWithThinkingListWrapper
    initial_prompt_template = INITIAL_PROMPT_TEMPLATE
    refine_prompt_template = REFINE_PROMPT_TEMPLATE
    section_name = "participants"
