from dataclasses import dataclass

from keycloak import KeycloakOpenID
from loguru import logger

from mcr_meeting.app.configs.base import KeycloakExchangeSettings
from mcr_meeting.app.services.redis_token_store import get_refresh_token, save_refresh_token


@dataclass(frozen=True)
class TokenRefreshResult:
    access_token: str
    rotated_refresh: str | None

_settings = KeycloakExchangeSettings()

_keycloak = KeycloakOpenID(
    server_url=_settings.KEYCLOAK_URL,
    client_id=_settings.KEYCLOAK_CORE_CLIENT_ID,
    client_secret_key=_settings.KEYCLOAK_CORE_CLIENT_SECRET,
    realm_name=_settings.KEYCLOAK_REALM,
)


def exchange_token_for_offline(access_token: str) -> str | None:
    # RFC 8693 token exchange: Exchanging a token signed for the frontend (client mcr)
    # for one signed fro the backend (client mcr-core)
    try:
        result: dict[str, str] = _keycloak.exchange_token(
            token=access_token,
            audience=_settings.KEYCLOAK_CORE_CLIENT_ID,
            scope="openid offline_access",
        )
        return result.get("refresh_token")
    except Exception:
        logger.exception("Token exchange failed")
        return None


def refresh_access_token(refresh_token: str) -> TokenRefreshResult:
    result: dict[str, str] = _keycloak.refresh_token(refresh_token)
    new_refresh = result.get("refresh_token")
    rotated = new_refresh if new_refresh != refresh_token else None
    return TokenRefreshResult(access_token=result["access_token"], rotated_refresh=rotated)


def ensure_offline_token(user_sub: str, access_token: str | None) -> None:
    if access_token is None:
        return

    try:
        refresh_token = exchange_token_for_offline(access_token)
        if refresh_token:
            save_refresh_token(user_sub, refresh_token)
    except Exception:
        logger.exception("ensure_offline_token failed for user {}", user_sub)
