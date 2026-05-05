from typing import Any

import httpx
from loguru import logger

from mcr_generation.app.client.http_client import HttpClient
from mcr_generation.app.configs.settings import ApiSettings
from mcr_generation.app.exceptions.exceptions import ReportCallbackError
from mcr_generation.app.schemas.base import BaseReport


class CoreApiClient:
    def __init__(self) -> None:
        self.api_settings = ApiSettings()
        self.client = HttpClient(base_url=self.api_settings.MCR_CORE_API_URL)

    def mark_report_success(self, meeting_id: int, report: BaseReport) -> None:
        self._post(
            f"/meetings/{meeting_id}/report/success",
            json=report.model_dump(),
        )

    def mark_report_failure(self, meeting_id: int) -> None:
        self._post(f"/meetings/{meeting_id}/report/failure")

    def mark_deliverable_success(
        self,
        deliverable_id: int,
        report: BaseReport,
        external_url: str | None = None,
    ) -> None:
        self._post(
            f"/deliverables/{deliverable_id}/success",
            json={
                "external_url": external_url,
                "report_response": report.model_dump(),
            },
            swallow_404=True,
        )

    def mark_deliverable_failure(self, deliverable_id: int) -> None:
        self._post(f"/deliverables/{deliverable_id}/failure", swallow_404=True)

    def _post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        *,
        swallow_404: bool = False,
    ) -> None:
        try:
            self.client.post(url, json=json)
        except httpx.HTTPStatusError as e:
            if swallow_404 and e.response.status_code == 404:
                logger.warning("Endpoint {} returned 404; dropping callback", url)
                return
            raise ReportCallbackError(f"Failed to POST callback to {url}: {e}") from e
        except Exception as e:
            raise ReportCallbackError(f"Failed to POST callback to {url}: {e}") from e
