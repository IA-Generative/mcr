from collections.abc import Mapping
from typing import Any

import httpx


class HttpClient:
    JsonParams = Mapping[str, str | int | float | bool | None]

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout: httpx.Timeout | None = None,
    ):
        self.base_url = base_url
        self.token = token
        self.timeout = timeout if timeout is not None else httpx.Timeout(5.0)

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-User-Keycloak-UUID"] = self.token
        return headers

    def get(self, endpoint: str, params: JsonParams | None = None) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.get(endpoint, headers=self._get_headers(), params=params)
            response.raise_for_status()
            return response

    def post(self, endpoint: str, json: Any = None) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.post(endpoint, headers=self._get_headers(), json=json)
            response.raise_for_status()
            return response
