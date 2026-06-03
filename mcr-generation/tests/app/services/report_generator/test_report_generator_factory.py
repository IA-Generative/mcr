"""Unit tests for the get_generator factory."""

import pytest

from mcr_generation.app.exceptions.exceptions import UnsupportedReportTypeError
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.report_generator import create_report_generator
from mcr_generation.app.services.report_generator.structured_minutes_generator import (
    StructuredMinutesGenerator,
)


class TestGetGenerator:
    def test_raises_unsupported_report_type_for_unknown_value(self) -> None:
        with pytest.raises(UnsupportedReportTypeError, match="Unknown report type"):
            create_report_generator("not-a-real-report-type")

    def test_returns_structured_minutes_generator(self) -> None:
        generator = create_report_generator(ReportTypes.STRUCTURED_MINUTES)
        assert isinstance(generator, StructuredMinutesGenerator)
