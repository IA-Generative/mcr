from mcr_generation.app.schemas.base import NextMeeting
from mcr_generation.app.services.sections.base.init_then_refine import (
    BaseInitThenRefine,
)
from mcr_generation.app.services.sections.next_meeting.prompts import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_NOTES_AUTHORITY_CLAUSE,
    REFINE_PROMPT_TEMPLATE,
)


class RefineNextMeeting(BaseInitThenRefine[NextMeeting]):
    response_model = NextMeeting
    initial_prompt_template = INITIAL_PROMPT_TEMPLATE
    refine_prompt_template = REFINE_PROMPT_TEMPLATE
    refine_notes_authority_clause = REFINE_NOTES_AUTHORITY_CLAUSE
    section_name = "next_meeting"
