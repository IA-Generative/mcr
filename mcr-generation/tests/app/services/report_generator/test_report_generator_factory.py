"""Unit tests for the get_generator factory."""

import pytest

from mcr_generation.app.exceptions.exceptions import UnsupportedReportTypeError
from mcr_generation.app.schemas.celery_types import ReportTypes
from mcr_generation.app.services.report_generator import create_report_generator


class TestGetGenerator:
    def test_raises_unsupported_report_type_for_unknown_value(self) -> None:
        with pytest.raises(UnsupportedReportTypeError, match="Unknown report type"):
            create_report_generator("not-a-real-report-type")

    def test_returns_narrative_synthesis_generator(self) -> None:
        # On compare par nom de classe + report_type plutôt que par isinstance :
        # les tests de générateurs rechargent leur module (sys.modules pop +
        # importlib), ce qui crée un objet-classe distinct selon l'ordre de
        # collecte et ferait échouer un isinstance basé sur l'identité.
        generator = create_report_generator(ReportTypes.NARRATIVE_SYNTHESIS)
        assert type(generator).__name__ == "NarrativeSynthesisGenerator"
        assert generator.report_type == ReportTypes.NARRATIVE_SYNTHESIS
