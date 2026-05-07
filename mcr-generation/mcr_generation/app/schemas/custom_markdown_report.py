from pydantic import BaseModel, ConfigDict


class CustomMarkdownReport(BaseModel):
    """Minimal v0 payload for custom reports — single markdown blob.

    Will be replaced by a multi-section payload (title + sections[]) once T3/T5
    introduce the rewriter and section assembly. Kept deliberately separate so
    we can drop it without touching the future schema.
    """

    model_config = ConfigDict(frozen=True)

    markdown: str
