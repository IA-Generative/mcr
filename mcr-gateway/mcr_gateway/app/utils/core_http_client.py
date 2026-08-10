import httpx

from mcr_gateway.setup.request_id_middleware import REQUEST_ID_HEADER, get_request_id


async def _forward_request_id(request: httpx.Request) -> None:
    request_id = get_request_id()
    if request_id:
        request.headers[REQUEST_ID_HEADER] = request_id


def core_client(
    *,
    base_url: str = "",
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    # Single builder for every gateway→core call so the request-id forwarding
    # hook is wired in one place instead of at each call site.
    return httpx.AsyncClient(
        base_url=base_url,
        auth=auth,
        event_hooks={"request": [_forward_request_id]},
    )
