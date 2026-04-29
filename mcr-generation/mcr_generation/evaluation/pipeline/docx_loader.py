"""Load `.docx` files as plain text for the evaluation pipeline.

Uses `python-docx` (already a dependency) to read paragraph text. We use plain
text rather than full DOCX semantics: G-Eval prompts work on natural-language
content, not on formatting.
"""

from pathlib import Path

from docx import Document


def load_docx_text(path: Path) -> str:
    """Concatenate every paragraph of the `.docx` at `path` into a single string."""
    document = Document(str(path))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def save_text_as_docx(text: str, path: Path) -> None:
    """Write `text` to a fresh `.docx` at `path`, one paragraph per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(str(path))
