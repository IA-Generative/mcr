from typing import Protocol

from mcr_generation.evaluation.pipeline.types import Criterion, ScoreResult


class Scorer(Protocol):
    def score(
        self,
        criterion: Criterion,
        report: str,
        reference: str | None,
    ) -> ScoreResult: ...
