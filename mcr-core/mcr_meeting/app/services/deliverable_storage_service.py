from loguru import logger

from mcr_meeting.app.client.drive_client import upload_file
from mcr_meeting.app.db.deliverable_repository import save_deliverable
from mcr_meeting.app.db.unit_of_work import UnitOfWork
from mcr_meeting.app.models.deliverable_model import (
    Deliverable,
    DeliverableStatus,
    DeliverableType,
)
from mcr_meeting.app.services.redis_token_store import (
    delete_refresh_token,
    get_refresh_token,
    save_refresh_token,
)
from mcr_meeting.app.services.token_exchange_service import refresh_access_token


def _acquire_fresh_access_token(user_keycloak_uuid: str) -> str:
    refresh_token = get_refresh_token(user_keycloak_uuid)
    if refresh_token is None:
        raise RuntimeError(
            f"No refresh token skipping Drive upload: user = {user_keycloak_uuid}"
        )

    try:
        token_refresh_result = refresh_access_token(refresh_token)
    except Exception as exc:
        delete_refresh_token(user_keycloak_uuid)
        raise RuntimeError(
            f"Refresh token failed for user = {user_keycloak_uuid}: {exc}"
        ) from exc

    if token_refresh_result.rotated_refresh:
        save_refresh_token(user_keycloak_uuid, token_refresh_result.rotated_refresh)
    return token_refresh_result.access_token


def store_deliverable(
    meeting_id: int,
    user_keycloak_uuid: str,
    file_bytes: bytes,
    type: DeliverableType,
    filename: str = "document.docx",
) -> None:
    try:
        access_token = _acquire_fresh_access_token(user_keycloak_uuid)

        external_url = upload_file(access_token, filename, file_bytes)

        with UnitOfWork():
            save_deliverable(
                Deliverable(
                    meeting_id=meeting_id,
                    type=type,
                    status=DeliverableStatus.AVAILABLE,
                    external_url=external_url,
                )
            )

    except Exception as exc:
        logger.exception(
            "Failed to store {} deliverable for meeting {}: {}",
            type.value,
            meeting_id,
            exc,
        )
