from dataclasses import dataclass

from keycloak import KeycloakOpenID
from loguru import logger

from mcr_meeting.app.configs.base import KeycloakExchangeSettings


@dataclass(frozen=True)
class TokenRefreshResult:
    access_token: str
    rotated_refresh: str | None


_settings = KeycloakExchangeSettings()

_KEYCLOAK_TIMEOUT_SECONDS = 10


def _is_keycloak_configured() -> bool:
    return bool(
        _settings.KEYCLOAK_URL
        and _settings.KEYCLOAK_REALM
        and _settings.KEYCLOAK_CORE_CLIENT_SECRET
    )


_keycloak: KeycloakOpenID | None = (
    KeycloakOpenID(
        server_url=_settings.KEYCLOAK_URL,
        client_id=_settings.KEYCLOAK_CORE_CLIENT_ID,
        client_secret_key=_settings.KEYCLOAK_CORE_CLIENT_SECRET,
        realm_name=_settings.KEYCLOAK_REALM,
        timeout=_KEYCLOAK_TIMEOUT_SECONDS,
    )
    if _is_keycloak_configured()
    else None
)


def exchange_token_for_offline(access_token: str) -> str | None:
    # RFC 8693 token exchange: Exchanging a token signed for the frontend (client mcr)
    # for one signed for the backend (client mcr-core)
    if _keycloak is None:
        return None
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
    if _keycloak is None:
        raise RuntimeError("Keycloak token exchange is not configured")
    result: dict[str, str] = _keycloak.refresh_token(refresh_token)
    new_refresh = result.get("refresh_token")
    rotated = new_refresh if new_refresh != refresh_token else None
    return TokenRefreshResult(
        access_token=result["access_token"], rotated_refresh=rotated
    )
