from mimetypes import guess_type

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


def guess_mime_type(filename: str) -> str:
    ext = filename.split(".")[1]
    type = guess_type(url=filename)[0]
    if not type and ext in REVERSE_MAP:
        # If no extension is found, default to .raw
        type = REVERSE_MAP[ext]
    return type or "application/octet-stream"
