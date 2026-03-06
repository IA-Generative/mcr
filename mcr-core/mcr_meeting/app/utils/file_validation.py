from mimetypes import guess_type
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import UploadFile

from mcr_meeting.app.exceptions.exceptions import InvalidFileError

# This is necessary because we use python 3.11 and some mimetypes are not registered in that version
MAP_EXTRA_EXTENSIONS = {
    "audio/weba": "weba",
    "audio/wav": "wav",
    "audio/ogg": "oga",
    "audio/aac": "aac",
    "audio/ac3": "ac3",
    "audio/amr": "amr",
    "audio/flac": "flac",
    "audio/mp4": "m4a",
    "audio/opus": "opus",
    "audio/vorbis": "ogg",  # stdlib maps ogg → audio/ogg, not audio/vorbis
    "audio/vnd.dts": "dts",
    "audio/vnd.dts.hd": "dtshd",
    "audio/webm": "webm",  # stdlib maps webm → video/webm
    "audio/x-flac": "flac",
    "audio/x-m4a": "m4a",
}
REVERSE_MAP = {v: k for k, v in MAP_EXTRA_EXTENSIONS.items()}

DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

DOCX_MAGIC_BYTES = b"PK\x03\x04"


def guess_mime_type(filename: str) -> str:
    ext = filename.split(".")[1]
    type = guess_type(url=filename)[0]
    if not type and ext in REVERSE_MAP:
        # If no extension is found, default to .raw
        type = REVERSE_MAP[ext]
    return type or "application/octet-stream"


async def validate_docx_upload(file: "UploadFile") -> None:
    if not (file.content_type and file.content_type == DOCX_MIME_TYPE):
        raise InvalidFileError(
            "Invalid file type. MimeType didn't match docx.",
            file.filename,
        )

    header = await file.read(4)
    await file.seek(0)

    if header != DOCX_MAGIC_BYTES:
        raise InvalidFileError(
            "Invalid file content. Magic bytes didn't match a DOCX file.",
            file.filename,
        )
