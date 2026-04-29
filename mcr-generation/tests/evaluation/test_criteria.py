"""Smoke checks on the criteria registry and `Criterion.render`."""

from mcr_generation.evaluation.criteria import (
    CRITERIA,
    NON_REDUNDANCY,
    PARTICIPANTS_ACCURACY,
)
from mcr_generation.evaluation.pipeline.types import Criterion


class TestCriteriaRegistry:
    def test_six_criteria_exposed_with_unique_names(self) -> None:
        names = [c.name for c in CRITERIA]
        assert len(CRITERIA) == 6
        assert len(set(names)) == len(names)

    def test_every_criterion_uses_the_one_to_five_scale(self) -> None:
        for criterion in CRITERIA:
            assert criterion.scale == (1, 5), criterion.name

    def test_scope_is_either_global_or_section(self) -> None:
        for criterion in CRITERIA:
            assert criterion.is_global or criterion.scope.startswith("section:"), (
                criterion.scope
            )


class TestCriterionRender:
    def test_substitutes_report_and_reference(self) -> None:
        criterion = Criterion(
            name="dummy",
            scope="global",
            scale=(1, 5),
            description="",
            prompt_template="REPORT={{report}} REF={{reference_report}}",
        )
        rendered = criterion.render(report="A", reference="B")
        assert rendered == "REPORT=A REF=B"

    def test_intrinsic_criterion_renders_without_reference_placeholder(self) -> None:
        # `non_redundancy` does not include `{{reference_report}}` in its template,
        # so a None reference must not leak the placeholder into the prompt.
        rendered = NON_REDUNDANCY.render(report="some report", reference=None)
        assert "{{reference_report}}" not in rendered
        assert "{{report}}" not in rendered
        assert "some report" in rendered

    def test_section_criterion_keeps_both_placeholders(self) -> None:
        rendered = PARTICIPANTS_ACCURACY.render(
            report="generated participants",
            reference="reference participants",
        )
        assert "generated participants" in rendered
        assert "reference participants" in rendered
        assert "{{report}}" not in rendered
        assert "{{reference_report}}" not in rendered
