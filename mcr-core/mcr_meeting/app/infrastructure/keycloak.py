from dataclasses import dataclass

from keycloak import KeycloakOpenID
from loguru import logger
from pydantic import ValidationError

from mcr_meeting.app.configs.base import KeycloakExchangeSettings
from mcr_meeting.app.exceptions.exceptions import TokenValidationError
from mcr_meeting.app.schemas.keycloak_claims import TokenClaims


@dataclass(frozen=True)
class TokenRefreshResult:
    access_token: str
    rotated_refresh: str | None


_settings = KeycloakExchangeSettings()

_KEYCLOAK_TIMEOUT_SECONDS = 10
FRONTEND_CLIENT_ID = _settings.KEYCLOAK_FRONTEND_CLIENT_ID


def _is_kc_public_endpoint_configured() -> bool:
    return bool(_settings.KEYCLOAK_URL and _settings.KEYCLOAK_REALM)


def _is_keycloak_configured() -> bool:
    return bool(
        _is_kc_public_endpoint_configured() and _settings.KEYCLOAK_CORE_CLIENT_SECRET
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

# Separate client dedicated to inbound token validation. decode_token only needs
# the realm public key (server_url + realm), so no client secret is required —
# signature verification is realm-wide, independent of which client is configured.
_keycloak_validator: KeycloakOpenID | None = (
    KeycloakOpenID(
        server_url=_settings.KEYCLOAK_URL,
        client_id=_settings.KEYCLOAK_FRONTEND_CLIENT_ID,
        client_secret_key="",
        realm_name=_settings.KEYCLOAK_REALM,
        timeout=_KEYCLOAK_TIMEOUT_SECONDS,
    )
    if _is_kc_public_endpoint_configured()
    else None
)


def decode_and_verify(token: str) -> TokenClaims:
    if _keycloak_validator is None:
        raise TokenValidationError("Keycloak token validation is not configured")
    try:
        raw = _keycloak_validator.decode_token(token)
    except Exception as exc:
        raise TokenValidationError("Invalid or expired token") from exc

    try:
        claims = TokenClaims.model_validate(raw)
    except ValidationError as exc:
        raise TokenValidationError("Token claims are missing or malformed") from exc

    if claims.azp != FRONTEND_CLIENT_ID:
        raise TokenValidationError("Token not issued for the frontend client")
    return claims


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
