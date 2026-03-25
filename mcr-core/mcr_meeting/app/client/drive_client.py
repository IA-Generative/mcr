from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType

import httpx
from loguru import logger

from mcr_meeting.app.configs.base import DriveSettings
from mcr_meeting.app.utils.file_validation import DOCX_MIME_TYPE

_settings = DriveSettings()


@dataclass(frozen=True)
class CreatedDriveItem:
    id: object
    presigned_url: str


class DriveClient:
    ITEMS_API_PATH = "/external_api/v1.0/items/"

    def __init__(self, access_token: str) -> None:
        self._client = httpx.Client(
            base_url=f"{_settings.DRIVE_API_BASE_URL}{self.ITEMS_API_PATH}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def __enter__(self) -> DriveClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._client.close()

    def initiate_upload(self, filename: str, file_bytes: bytes) -> CreatedDriveItem:
        response = self._client.post(
            "",
            data={"type": "file", "filename": filename},
            files={"file": (filename, file_bytes, DOCX_MIME_TYPE)},
        )
        response.raise_for_status()
        data: dict[str, object] = response.json()
        item = CreatedDriveItem(
            id=data["id"], presigned_url=str(data.get("policy", ""))
        )

        return item

    def confirm_upload(self, item_id: object) -> str:
        response = self._client.post(f"{item_id}/upload-ended/")
        response.raise_for_status()
        return f"{_settings.DRIVE_FRONTEND_URL}/explorer/items/files/{item_id}"


def upload_to_presigned_url(item: CreatedDriveItem, file_bytes: bytes) -> None:
    if item.presigned_url:
        resp = httpx.put(
            item.presigned_url,
            content=file_bytes,
            headers={"Content-Type": DOCX_MIME_TYPE, "x-amz-acl": "private"},
        )
        resp.raise_for_status()
    else:
        logger.warning("No presigned URL for item {}, skipping S3 upload", item.id)


def upload_file(access_token: str, filename: str, file_bytes: bytes) -> str:
    with DriveClient(access_token) as client:
        item = client.initiate_upload(filename, file_bytes)
        upload_to_presigned_url(item, file_bytes)
        external_url = client.confirm_upload(item.id)
        logger.info("Uploaded {} to Drive: {}", filename, external_url)
        return external_url
