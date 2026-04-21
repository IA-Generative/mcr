from mcr_generation.app.exceptions.exceptions import UnsupportedReportTypeError
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.report_generator.base_report_generator import (
    BaseReportGenerator,
)
from mcr_generation.app.services.report_generator.decision_record_generator import (
    DecisionRecordGenerator,
)
from mcr_generation.app.services.report_generator.detailed_synthesis_generator import (
    DetailedSynthesisGenerator,
)


def get_generator(report_type: ReportTypes) -> BaseReportGenerator:
    """
    Factory function that returns the appropriate report generator for the given report type.

    Args:
        report_type (ReportTypes): The type of report to generate.

    Returns:
        BaseReportGenerator: A concrete report generator instance.

    Raises:
        UnsupportedReportTypeError: If the report type is not supported.
    """
    match report_type:
        case ReportTypes.DECISION_RECORD:
            return DecisionRecordGenerator()
        case ReportTypes.DETAILED_SYNTHESIS:
            return DetailedSynthesisGenerator()
        case _:
            raise UnsupportedReportTypeError(f"Unknown report type: {report_type}")
