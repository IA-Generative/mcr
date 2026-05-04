"""Offline evaluation pipeline orchestrator.

Flow per item:
1. Load transcript → chunks via `chunk_docx_to_document_list`.
2. Generate a `BaseReport` via the existing report generator.
3. Render the report to markdown and persist it under `outputs/generated_reports/`.
4. Score each `Criterion` via the G-Eval scorer:
   - `scope=global` → compare full markdown vs `expected/reports/<uid>.docx`.
   - `scope=section:X` → split section X then compare vs `expected/<X>/<uid>.docx`.
5. Aggregate every item into a CSV + summary JSON.
"""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from loguru import logger

from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.report_generator import get_generator
from mcr_generation.app.services.utils.input_chunker import chunk_docx_to_document_list
from mcr_generation.evaluation.criteria import CRITERIA
from mcr_generation.evaluation.pipeline.csv_writer import write_csv, write_summary
from mcr_generation.evaluation.pipeline.docx_loader import (
    load_docx_text,
    save_text_as_docx,
)
from mcr_generation.evaluation.pipeline.layout import DatasetLayout, OutputLayout
from mcr_generation.evaluation.pipeline.report_renderer import render_report
from mcr_generation.evaluation.pipeline.section_splitter import extract_section
from mcr_generation.evaluation.pipeline.types import (
    Criterion,
    EvalItem,
    ItemRunResult,
    RunSummary,
    ScoreResult,
)
from mcr_generation.evaluation.scorers.base import Scorer
from mcr_generation.evaluation.scorers.g_eval import GEvalScorer


class ReportEvaluationPipeline:
    def __init__(
        self,
        data_dir: Path,
        output_dir: Path,
        report_type: ReportTypes = ReportTypes.DECISION_RECORD,
        scorer: Scorer | None = None,
    ) -> None:
        self._dataset = DatasetLayout(data_dir=data_dir)
        self._output = OutputLayout(output_dir=output_dir)
        self._report_type = report_type
        self._scorer: Scorer = scorer or GEvalScorer()

    def run(self, limit: int | None = None) -> RunSummary:
        run_id = self._build_run_id()
        items = self._discover_items(limit=limit)
        if not items:
            logger.error("No transcripts found in {}.", self._dataset.transcripts_dir)
            raise ValueError(
                "No transcripts found in the transcript dir of the dataset"
            )

        logger.info("Run {}: {} item(s) to process.", run_id, len(items))
        results: list[ItemRunResult] = []
        for index, item in enumerate(items, start=1):
            logger.info("[{}/{}] Processing {}", index, len(items), item.uid)
            results.append(self._run_item(item))

        return self._finalize(run_id=run_id, results=results)

    # ----- discovery -------------------------------------------------------

    def _discover_items(self, limit: int | None) -> list[EvalItem]:
        section_names = list(
            dict.fromkeys(
                c.section_name for c in CRITERIA if c.section_name is not None
            )
        )
        items: list[EvalItem] = []
        for transcript_path in sorted(self._dataset.transcripts_dir.glob("*.docx")):
            uid = transcript_path.stem
            expected_report = self._dataset.expected_report(uid)
            expected_sections: dict[str, Path] = {}
            for section in section_names:
                candidate = self._dataset.expected_section(uid, section)
                if candidate.exists():
                    expected_sections[section] = candidate
            items.append(
                EvalItem(
                    uid=uid,
                    transcript_path=transcript_path,
                    expected_report_path=(
                        expected_report if expected_report.exists() else None
                    ),
                    expected_section_paths=expected_sections,
                )
            )
        if limit is not None:
            items = items[:limit]
        self._validate_references(items)
        return items

    def _validate_references(self, items: list[EvalItem]) -> None:
        missing: list[Path] = []
        for item in items:
            for criterion in CRITERIA:
                if "{{reference_report}}" not in criterion.prompt_template:
                    continue
                if criterion.is_global:
                    path = self._dataset.expected_report(item.uid)
                else:
                    section_name = criterion.section_name
                    assert section_name is not None
                    path = self._dataset.expected_section(item.uid, section_name)
                if not path.exists():
                    missing.append(path)
        if missing:
            listing = "\n  - ".join(str(p) for p in missing)
            raise ValueError(
                f"Dataset is incomplete: {len(missing)} reference file(s) "
                f"missing:\n  - {listing}"
            )

    # ----- per-item run ----------------------------------------------------

    def _run_item(self, item: EvalItem) -> ItemRunResult:
        try:
            generated_markdown = self._generate_report(item)
        except Exception as exc:
            logger.opt(exception=exc).error("Generation failed for {}", item.uid)
            empty_scores = {c.name: ScoreResult(value=None) for c in CRITERIA}
            return ItemRunResult(uid=item.uid, scores=empty_scores, error=str(exc))

        scores: dict[str, ScoreResult] = {}
        for criterion in CRITERIA:
            scores[criterion.name] = self._score_criterion(
                criterion=criterion,
                item=item,
                generated_markdown=generated_markdown,
            )
        return ItemRunResult(uid=item.uid, scores=scores)

    def _generate_report(self, item: EvalItem) -> str:
        with item.transcript_path.open("rb") as fh:
            chunks = chunk_docx_to_document_list(BytesIO(fh.read()))
        generator = get_generator(self._report_type)
        report = generator.generate(chunks)
        markdown = render_report(report)
        save_text_as_docx(markdown, self._output.generated_report(item.uid))
        return markdown

    def _score_criterion(
        self,
        criterion: Criterion,
        item: EvalItem,
        generated_markdown: str,
    ) -> ScoreResult:
        report_text, reference_text = self._extract_inputs(
            criterion=criterion,
            item=item,
            generated_markdown=generated_markdown,
        )
        if report_text is None:
            logger.warning(
                "Section '{}' not found in generated report for criterion {}.",
                criterion.section_name,
                criterion.name,
            )
            return ScoreResult(
                value=None,
                justification=(
                    f"Section '{criterion.section_name}' not found in generated report."
                ),
            )
        return self._scorer.score(criterion, report_text, reference_text)

    def _extract_inputs(
        self,
        criterion: Criterion,
        item: EvalItem,
        generated_markdown: str,
    ) -> tuple[str | None, str | None]:
        if criterion.is_global:
            reference = (
                load_docx_text(item.expected_report_path)
                if item.expected_report_path is not None
                else None
            )
            return generated_markdown, reference

        section_name = criterion.section_name
        assert section_name is not None  # invariant: non-global ⇒ section:<name>
        section_text = extract_section(generated_markdown, section_name)
        reference_path = item.expected_section_paths.get(section_name)
        reference = load_docx_text(reference_path) if reference_path else None
        return section_text, reference

    # ----- finalization ----------------------------------------------------

    def _finalize(self, run_id: str, results: list[ItemRunResult]) -> RunSummary:
        metrics_dir = self._output.metrics_dir
        csv_path = metrics_dir / f"{run_id}.csv"
        summary_path = metrics_dir / f"{run_id}_summary.json"

        criteria_means = write_csv(csv_path, CRITERIA, results)

        all_values = [
            v for cm in criteria_means.values() if cm is not None for v in [cm]
        ]
        overall_mean = (
            round(sum(all_values) / len(all_values), 2) if all_values else None
        )

        n_total = len(results)
        n_failed = sum(1 for r in results if r.error is not None)
        summary = RunSummary(
            run_id=run_id,
            timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            dataset_dir=str(self._dataset.data_dir),
            n_items_total=n_total,
            n_items_succeeded=n_total - n_failed,
            n_items_failed=n_failed,
            criteria_means=criteria_means,
            overall_mean=overall_mean,
        )
        write_summary(summary_path, summary)
        logger.info("Wrote {}", csv_path)
        logger.info("Wrote {}", summary_path)
        return summary

    # ----- helpers ---------------------------------------------------------

    @staticmethod
    def _build_run_id() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
