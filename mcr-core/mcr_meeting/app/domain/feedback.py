import re
from urllib.parse import urlparse


def extract_meeting_id_from_url(url: str) -> int | None:
    path = urlparse(url).path
    match = re.search(r"/meetings/(\d+)", path)
    if match:
        return int(match.group(1))
    return None
