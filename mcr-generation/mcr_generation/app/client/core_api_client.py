from typing import Any

import httpx
from loguru import logger
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mcr_generation.app.client.http_client import HttpClient
from mcr_generation.app.configs.settings import ApiSettings, InProgressCallbackSettings
from mcr_generation.app.exceptions.exceptions import (
    DeliverableNotYetVisibleError,
    ReportCallbackError,
)
from mcr_generation.app.schemas.base import BaseReport, CustomMarkdownReport


class CoreApiClient:
    def __init__(self) -> None:
        self.api_settings = ApiSettings()
        self.in_progress_settings = InProgressCallbackSettings()
        self.client = HttpClient(base_url=self.api_settings.MCR_CORE_API_URL)

    def mark_deliverable_in_progress(self, deliverable_id: int) -> None:
        for attempt in Retrying(
            stop=stop_after_attempt(
                self.in_progress_settings.IN_PROGRESS_RETRY_MAX_ATTEMPTS
            ),
            wait=wait_exponential(
                multiplier=self.in_progress_settings.IN_PROGRESS_RETRY_WAIT_MULTIPLIER,
                min=self.in_progress_settings.IN_PROGRESS_RETRY_MIN_WAIT,
                max=self.in_progress_settings.IN_PROGRESS_RETRY_MAX_WAIT,
            ),
            retry=retry_if_exception_type(DeliverableNotYetVisibleError),
            reraise=True,
        ):
            with attempt:
                self._post(
                    f"/deliverables/{deliverable_id}/in_progress",
                    swallow_409=True,
                )

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
        self._post(f"/deliverables/{deliverable_id}/failure", swallow_404=True)

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
