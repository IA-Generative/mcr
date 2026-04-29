"""Unit tests for the get_generator factory."""

import pytest

from mcr_generation.app.exceptions.exceptions import UnsupportedReportTypeError
from mcr_generation.app.services.report_generator import get_generator


class TestGetGenerator:
    def test_raises_unsupported_report_type_for_unknown_value(self) -> None:
        with pytest.raises(UnsupportedReportTypeError, match="Unknown report type"):
            get_generator("not-a-real-report-type")
