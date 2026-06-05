from mcr_generation.app.schemas.base import (
    ParticipantsHint,
    ParticipantsWithThinkingListWrapper,
)
from mcr_generation.app.services.sections.base.init_then_refine import (
    BaseInitThenRefine,
)
from mcr_generation.app.services.sections.participants.prompts import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
    render_participants_hint,
)


class RefineParticipants(BaseInitThenRefine[ParticipantsWithThinkingListWrapper]):
    response_model = ParticipantsWithThinkingListWrapper
    initial_prompt_template = INITIAL_PROMPT_TEMPLATE
    refine_prompt_template = REFINE_PROMPT_TEMPLATE
    section_name = "participants"

    def __init__(self, participants_hint: ParticipantsHint | None = None) -> None:
        super().__init__()
        self._notes_hint = render_participants_hint(participants_hint)

    def _extra_prompt_vars(self) -> dict[str, str]:
        return {"notes_hint": self._notes_hint}
