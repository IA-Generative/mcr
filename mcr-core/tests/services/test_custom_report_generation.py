from docx import Document

from mcr_meeting.app.schemas.report_generation import (
    CustomReportResponse,
    DetailedSynthesisGenerationResponse,
    ReportGenerationResponse,
    ReportHeader,
    is_custom_report,
)
from mcr_meeting.app.services.docx_report_generation_service import (
    generate_custom_report_docx,
)


def _build_fake_custom_report() -> CustomReportResponse:
    return CustomReportResponse(
        markdown_content="""\
## Synthèse

Le projet avance bien.

## Risques identifiés

- Retard possible sur le lot 2
- Dépendance externe non confirmée
""",
    )


class TestIsCustomReport:
    def test_true_for_custom_report_response(self) -> None:
        response = CustomReportResponse(markdown_content="test")
        assert is_custom_report(response) is True

    def test_false_for_detailed_synthesis(self) -> None:
        response = DetailedSynthesisGenerationResponse(
            header=ReportHeader(
                title="t", objective=None, participants=[], next_meeting=None
            ),
            discussions_summary=[],
            detailed_discussions=[],
            to_do_list=[],
            to_monitor_list=[],
        )
        assert is_custom_report(response) is False

    def test_false_for_decision_record(self) -> None:
        response = ReportGenerationResponse(
            header=ReportHeader(
                title="t", objective=None, participants=[], next_meeting=None
            ),
            topics_with_decision=[],
            next_steps=[],
        )
        assert is_custom_report(response) is False


class TestGenerateCustomReportDocx:
    def test_returns_non_empty_bytesio(self) -> None:
        response = _build_fake_custom_report()
        result = generate_custom_report_docx(response)
        assert result.getvalue()

    def test_docx_contains_markdown_content(self) -> None:
        response = _build_fake_custom_report()
        result = generate_custom_report_docx(response)

        doc = Document(result)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Synthèse" in full_text
        assert "Risques identifiés" in full_text
        assert "Retard possible sur le lot 2" in full_text
