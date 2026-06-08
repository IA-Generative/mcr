from loguru import logger

from mcr_meeting.app.infrastructure.keycloak import exchange_token_for_offline
from mcr_meeting.app.infrastructure.redis import save_refresh_token


def ensure_offline_token(user_sub: str, access_token: str | None) -> None:
    if access_token is None:
        return

    try:
        refresh_token = exchange_token_for_offline(access_token)
        if refresh_token:
            save_refresh_token(user_sub, refresh_token)
    except Exception:
        logger.exception("ensure_offline_token failed for user {}", user_sub)
