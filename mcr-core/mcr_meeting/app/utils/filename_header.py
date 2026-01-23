from typing import Mapping
from urllib.parse import quote


def create_safe_filename_header(filename: str) -> Mapping[str, str]:
    url_encoded_filename = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{url_encoded_filename}"
    }
    return headers
