from typing import Any

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

    def _post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.client.post(url, json=json)
        except Exception as e:
            raise ReportCallbackError(
                f"Failed to POST callback to {url}: {e}"
            ) from e
