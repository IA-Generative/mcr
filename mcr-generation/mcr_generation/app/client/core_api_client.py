from typing import Any

import httpx
from loguru import logger

from mcr_generation.app.client.http_client import HttpClient
from mcr_generation.app.configs.settings import ApiSettings, InProgressCallbackSettings
from mcr_generation.app.exceptions.exceptions import (
    DeliverableNotYetVisibleError,
    ReportCallbackError,
)
from mcr_generation.app.schemas.base import BaseReport, CustomMarkdownReport
from mcr_generation.app.utils.retry import retry_transient

_in_progress_settings = InProgressCallbackSettings()

_retry_in_progress = retry_transient(
    on=(DeliverableNotYetVisibleError,),
    attempts=_in_progress_settings.IN_PROGRESS_RETRY_MAX_ATTEMPTS,
    initial_delay=_in_progress_settings.IN_PROGRESS_RETRY_MIN_WAIT,
    max_delay=_in_progress_settings.IN_PROGRESS_RETRY_MAX_WAIT,
)


class CoreApiClient:
    def __init__(self) -> None:
        self.api_settings = ApiSettings()
        self.client = HttpClient(base_url=self.api_settings.MCR_CORE_API_URL)

    @_retry_in_progress
    def mark_deliverable_in_progress(self, deliverable_id: int) -> None:
        self._post(f"/deliverables/{deliverable_id}/start", swallow_409=True)

    def mark_deliverable_success(
        self,
        deliverable_id: int,
        report: BaseReport | CustomMarkdownReport,
    ) -> None:
        self._post(
            f"/deliverables/{deliverable_id}/success",
            json={"report_response": report.model_dump()},
            swallow_404=True,
        )

    def mark_deliverable_failure(self, deliverable_id: int) -> None:
        self._post(f"/deliverables/{deliverable_id}/fail", swallow_404=True)

    def _post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        *,
        swallow_404: bool = False,
        swallow_409: bool = False,
    ) -> None:
        try:
            self.client.post(url, json=json)
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if swallow_404 and status_code == 404:
                logger.warning("Endpoint {} returned 404; dropping callback", url)
                return
            if swallow_409 and status_code == 409:
                logger.warning(
                    "Endpoint {} returned 409; deliverable already past PENDING", url
                )
                return
            if status_code == 404:
                raise DeliverableNotYetVisibleError(
                    f"Deliverable not visible yet at {url}: {e}"
                ) from e
            raise ReportCallbackError(f"Failed to POST callback to {url}: {e}") from e
        except Exception as e:
            raise ReportCallbackError(f"Failed to POST callback to {url}: {e}") from e
