import os
from io import BytesIO

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

_ENV = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


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
    from .markdown_to_docx import markdown_to_docx

    md = render_markdown_template(template_name, data)
    return markdown_to_docx(md, style_template_path, styles_names)
