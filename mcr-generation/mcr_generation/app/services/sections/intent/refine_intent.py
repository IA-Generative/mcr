from mcr_generation.app.schemas.base import Intent
from mcr_generation.app.services.sections.base.init_then_refine import (
    BaseInitThenRefine,
)
from mcr_generation.app.services.sections.intent.prompts import (
    INITIAL_PROMPT_TEMPLATE,
    REFINE_PROMPT_TEMPLATE,
)


class RefineIntent(BaseInitThenRefine[Intent]):
    response_model = Intent
    initial_prompt_template = INITIAL_PROMPT_TEMPLATE
    refine_prompt_template = REFINE_PROMPT_TEMPLATE
    section_name = "intent"
