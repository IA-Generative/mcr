from collections.abc import Mapping

import httpx
from loguru import logger


class HttpClient:
    JsonParams = Mapping[str, str | int | float | bool | None]

    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url
        self.token = token

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-User-Keycloak-UUID"] = self.token
        return headers

    async def post(
        self,
        endpoint: str,
        data: object | None = None,
        *,
        swallow_404: bool = False,
    ) -> httpx.Response | None:
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.post(
                endpoint, headers=self._get_headers(), json=data
            )
            if swallow_404 and response.status_code == httpx.codes.NOT_FOUND:
                logger.warning("Endpoint {} returned 404; dropping call", endpoint)
                return None
            response.raise_for_status()
            return response

    async def get(
        self, endpoint: str, params: JsonParams | None = None
    ) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.get(
                endpoint, headers=self._get_headers(), params=params
            )
            response.raise_for_status()
            return response

    async def delete(self, endpoint: str) -> httpx.Response:
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            response = await client.delete(endpoint, headers=self._get_headers())
            response.raise_for_status()
            return response
