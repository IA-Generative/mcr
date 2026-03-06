import tempfile
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from markdowntodocx.markdownconverter import (  # type: ignore[import-untyped]
    convertMarkdownInFile,
)

# Styles required by markdowntodocx even if unused in the markdown content.
_REQUIRED_PARAGRAPH_STYLES = ("Code", "No Spacing", "List Paragraph")
_REQUIRED_CHARACTER_STYLES = ("Code Car",)
_REQUIRED_TABLE_STYLES = ("Table Grid",)


def _ensure_required_styles(doc: DocxDocument) -> None:
    # markdowntodocx expects a set of style to convert most markdown element to docx
    # but these style are missing from basic word documents. We ensure that they are always present
    # even if the template changes
    existing = {s.name for s in doc.styles}
    for name in _REQUIRED_PARAGRAPH_STYLES:
        if name not in existing:
            doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    for name in _REQUIRED_CHARACTER_STYLES:
        if name not in existing:
            doc.styles.add_style(name, WD_STYLE_TYPE.CHARACTER)
    for name in _REQUIRED_TABLE_STYLES:
        if name not in existing:
            doc.styles.add_style(name, WD_STYLE_TYPE.TABLE)


def markdown_to_docx(
    md_string: str,
    style_template_path: str,
    styles_names: dict[str, str] | None = None,
) -> BytesIO:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "report.docx"

        # Load style template + inject markdown as plain text paragraphs
        doc = Document(style_template_path)
        _ensure_required_styles(doc)
        for line in md_string.split("\n"):
            doc.add_paragraph(line)
        doc.save(str(tmp_path))

        success, result = convertMarkdownInFile(
            str(tmp_path), str(tmp_path), styles_names
        )
        if not success:
            raise RuntimeError(f"markdowntodocx conversion failed: {result}")

        return BytesIO(tmp_path.read_bytes())
