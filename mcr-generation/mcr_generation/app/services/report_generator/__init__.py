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


def create_report_generator(
    report_type: ReportTypes,
    *,
    custom_prompt: str | None = None,
) -> BaseReportGenerator | CustomReportGenerator:
    match report_type:
        case ReportTypes.DECISION_RECORD:
            return DecisionRecordGenerator()
        case ReportTypes.DETAILED_SYNTHESIS:
            return DetailedSynthesisGenerator()
        case ReportTypes.CUSTOM_REPORT:
            if custom_prompt is None:
                raise MissingCustomPromptError(
                    "CUSTOM_REPORT requires a non-empty custom_prompt"
                )
            return CustomReportGenerator(instruction=custom_prompt)
        case _:
            raise UnsupportedReportTypeError(f"Unknown report type: {report_type}")
