from mcr_generation.app.exceptions.exceptions import (
    MissingCustomPromptError,
    UnsupportedReportTypeError,
)
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.report_generator.base_report_generator import (
    BaseReportGenerator,
)
from mcr_generation.app.services.report_generator.custom_report_generator import (
    CustomReportGenerator,
)
from mcr_generation.app.services.report_generator.decision_record_generator import (
    DecisionRecordGenerator,
)
from mcr_generation.app.services.report_generator.detailed_synthesis_generator import (
    DetailedSynthesisGenerator,
)
from mcr_generation.app.services.report_generator.narrative_synthesis_generator import (
    NarrativeSynthesisGenerator,
)


def create_report_generator(
    report_type: ReportTypes,
    *,
    custom_prompt: str | None = None,
) -> BaseReportGenerator | CustomReportGenerator | NarrativeSynthesisGenerator:
    """
    Factory function that returns the appropriate report generator for the given report type.

    Args:
        report_type (ReportTypes): The type of report to generate.
        custom_prompt (str | None): End-user instruction. Required for
            CUSTOM_REPORT, ignored for the structured report types.

    Returns:
        A concrete report generator instance (structured, custom, or narrative).

    Raises:
        UnsupportedReportTypeError: If the report type is not supported.
        MissingCustomPromptError: If CUSTOM_REPORT is requested without a prompt.
    """
    match report_type:
        case ReportTypes.DECISION_RECORD:
            return DecisionRecordGenerator()
        case ReportTypes.DETAILED_SYNTHESIS:
            return DetailedSynthesisGenerator()
        case ReportTypes.NARRATIVE_SYNTHESIS:
            return NarrativeSynthesisGenerator()
        case ReportTypes.CUSTOM_REPORT:
            if custom_prompt is None:
                raise MissingCustomPromptError(
                    "CUSTOM_REPORT requires a non-empty custom_prompt"
                )
            return CustomReportGenerator(raw_prompt=custom_prompt)
        case _:
            raise UnsupportedReportTypeError(f"Unknown report type: {report_type}")
