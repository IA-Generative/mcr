import os
import tempfile
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markdowntodocx.markdownconverter import (  # type: ignore[import-untyped]
    convertMarkdownInFile,
)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "report_templates")

_ENV = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

# Styles required by markdowntodocx even if unused in the markdown content.
# markdowntodocx looks some of these up by literal key (e.g. styles["Cell"] in
# fill_cell, styles["footnote text"] / styles["footnote reference"] in the
# footnote path) — bypassing its own resolver — so the document must define
# them or the table / footnote branches raise KeyError.
_REQUIRED_PARAGRAPH_STYLES = (
    "Code",
    "No Spacing",
    "List Paragraph",
    "Cell",
    "footnote text",
)
_REQUIRED_CHARACTER_STYLES = ("Code Car", "footnote reference")
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


def render_markdown_template(template_name: str, data: dict) -> str:  # type: ignore[type-arg]
    """Load a .jinja.md template and render it with data."""
    return _ENV.get_template(template_name).render(**data)


def render_to_docx(
    template_name: str,
    data: dict,  # type: ignore[type-arg]
    style_template_path: str,
    styles_names: dict[str, str] | None = None,
) -> BytesIO:
    """Full pipeline: .jinja.md template file -> markdown -> DOCX."""
    md = render_markdown_template(template_name, data)
    return markdown_to_docx(md, style_template_path, styles_names)
