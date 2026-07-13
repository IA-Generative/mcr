from loguru import logger

from mcr_meeting.app.domain.deliverable_filename import build_deliverable_filename
from mcr_meeting.app.infrastructure.drive import upload_file
from mcr_meeting.app.infrastructure.keycloak import (
    TokenRefreshResult,
    refresh_access_token,
)
from mcr_meeting.app.infrastructure.redis import (
    delete_refresh_token,
    get_refresh_token,
    save_refresh_token,
)
from mcr_meeting.app.models import Meeting
from mcr_meeting.app.models.deliverable_model import DeliverableType


def try_upload_deliverable_to_drive(
    meeting: Meeting, deliverable_type: DeliverableType, file_bytes: bytes
) -> str | None:
    token = _try_acquire_token(meeting)
    if token is None:
        return None

    filename = build_deliverable_filename(deliverable_type, meeting.name or "")
    return _try_post_drive(token, filename, file_bytes)


def _try_acquire_token(meeting: Meeting) -> TokenRefreshResult | None:
    user_sub = str(meeting.owner.keycloak_uuid)

    refresh_token = get_refresh_token(user_sub)
    if refresh_token is None:
        logger.info("No refresh token for user {}; skipping Drive upload", user_sub)
        return None

    try:
        token_result = refresh_access_token(refresh_token)
    except Exception:
        delete_refresh_token(user_sub)
        logger.warning(
            "Drive token refresh failed for user {}; skipping upload", user_sub
        )
        return None

    if token_result.rotated_refresh:
        save_refresh_token(user_sub, token_result.rotated_refresh)

    return token_result


def _try_post_drive(
    token: TokenRefreshResult, filename: str, file_bytes: bytes
) -> str | None:
    try:
        return upload_file(token.access_token, filename, file_bytes)
    except Exception:
        logger.warning("Drive upload failed")
        return None
