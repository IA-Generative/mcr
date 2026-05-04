"""On-disk layout helpers for the offline evaluation pipeline.

Centralizes every subpath the pipeline reads from or writes to, so the
orchestrator never spells layout strings inline.
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class DatasetLayout(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_dir: Path

    @property
    def transcripts_dir(self) -> Path:
        return self.data_dir / "transcripts"

    @property
    def expected_root(self) -> Path:
        return self.data_dir / "expected"

    def expected_report(self, uid: str) -> Path:
        return self.expected_root / "reports" / f"{uid}.docx"

    def expected_section(self, uid: str, section_name: str) -> Path:
        return self.expected_root / section_name / f"{uid}.docx"


class OutputLayout(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_dir: Path

    def generated_report(self, uid: str) -> Path:
        return self.output_dir / "generated_reports" / f"{uid}.docx"

    @property
    def metrics_dir(self) -> Path:
        return self.output_dir / "metrics"
