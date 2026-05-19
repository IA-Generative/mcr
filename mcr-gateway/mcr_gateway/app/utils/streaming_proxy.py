import httpx
from fastapi.responses import StreamingResponse

_FORWARDED_HEADERS = ("content-disposition",)


def proxy_streaming_response(upstream: httpx.Response) -> StreamingResponse:
    headers = {
        header: upstream.headers[header]
        for header in _FORWARDED_HEADERS
        if header in upstream.headers
    }
    return StreamingResponse(
        upstream.aiter_bytes(),
        media_type=upstream.headers.get("content-type"),
        headers=headers,
    )
