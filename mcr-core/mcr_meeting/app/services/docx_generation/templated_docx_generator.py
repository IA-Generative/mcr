import os
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any

from docxtpl import DocxTemplate


class TemplatedDocxGenerator(ABC):
    def __init__(self, filename: str):
        template_path = os.path.join(
            os.getcwd(), "mcr_meeting", "app", "cr-templates", filename
        )
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template file not found at {template_path}")

        self.doc = DocxTemplate(template_path)

    @abstractmethod
    def build_context(self, *args: Any, **kwargs: Any) -> dict[str, Any]:  # type: ignore[explicit-any]
        """
        Must return a dict with all placeholders needed by the template.
        """
        ...

    @abstractmethod
    def fill_templated_doc(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[explicit-any]
        ...

    def save_and_return_docx(self) -> BytesIO:
        docx_io = BytesIO()
        self.doc.save(docx_io)
        docx_io.seek(0)  # Reset the buffer position to the beginning
        return docx_io
