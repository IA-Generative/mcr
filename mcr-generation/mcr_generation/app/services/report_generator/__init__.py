from mcr_generation.app.exceptions.exceptions import UnsupportedReportTypeError
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

# Union temporaire: CustomReportGenerator ne dérive pas de BaseReportGenerator
# (sortie markdown vs BaseReport structuré). À harmoniser en T5.
_Generator = BaseReportGenerator | CustomReportGenerator


def get_generator(report_type: ReportTypes) -> _Generator:
    """
    Factory function that returns the appropriate report generator for the given report type.

    Args:
        report_type (ReportTypes): The type of report to generate.

    Returns:
        BaseReportGenerator | CustomReportGenerator: A concrete report generator instance.

    Raises:
        UnsupportedReportTypeError: If the report type is not supported.
    """
    match report_type:
        case ReportTypes.DECISION_RECORD:
            return DecisionRecordGenerator()
        case ReportTypes.DETAILED_SYNTHESIS:
            return DetailedSynthesisGenerator()
        case ReportTypes.CUSTOM:
            return CustomReportGenerator()
        case _:
            raise UnsupportedReportTypeError(f"Unknown report type: {report_type}")
