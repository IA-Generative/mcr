from loguru import logger

from mcr_meeting.app.client.drive_client import upload_file
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


def upload_authenticated_for_user(
    user_keycloak_uuid: str, filename: str, content: bytes
) -> str:
    access_token = _acquire_fresh_access_token(user_keycloak_uuid)
    return upload_file(access_token, filename, content)


def try_upload_to_drive(
    user_keycloak_uuid: str, filename: str, content: bytes
) -> str | None:
    try:
        return upload_authenticated_for_user(
            user_keycloak_uuid=user_keycloak_uuid,
            filename=filename,
            content=content,
        )
    except Exception:
        logger.exception(
            "Drive upload failed for user {} (filename {})",
            user_keycloak_uuid,
            filename,
        )
        return None
