from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Criterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    scope: str  # "global" or "section:<name>" (e.g. "section:topics")
    scale: tuple[int, int]
    description: str
    prompt_template: str

    def render(self, report: str, reference: str | None) -> str:
        return self.prompt_template.replace("{{report}}", report).replace(
            "{{reference_report}}", reference or ""
        )

    @property
    def section_name(self) -> str | None:
        if self.scope.startswith("section:"):
            return self.scope.split(":", 1)[1]
        return None

    @property
    def is_global(self) -> bool:
        return self.scope == "global"


class ScoreResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: int | None
    justification: str | None = None


class EvalItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    uid: str
    transcript_path: Path
    expected_report_path: Path | None
    expected_section_paths: dict[str, Path] = Field(default_factory=dict)


class ItemRunResult(BaseModel):
    uid: str
    scores: dict[str, ScoreResult]
    error: str | None = None


class RunSummary(BaseModel):
    run_id: str
    timestamp_utc: str
    dataset_dir: str
    n_items_total: int
    n_items_succeeded: int
    n_items_failed: int
    criteria_means: dict[str, float | None]
    overall_mean: float | None
