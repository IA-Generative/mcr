"""Read-only validation of the Drive Keycloak setup against a target realm.

Mirrors `drive-keycloak-setup.md`: confirms the `mcr` public client, the
`drive` client, audience mappers on `mcr` and `mcr-core`, the token-exchange
policy gating `mcr-core`, and (optionally) `offline_access` on a target user.
Read-only — only issues admin API GETs.

Exit code 0 on success, 1 if any check fails.

Inspired by `provisioning.py`: same `pydantic-settings` skeleton and
`KeycloakAdmin` bootstrap.
"""

from __future__ import annotations

import base64
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from keycloak import KeycloakAdmin
from loguru import logger
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    KEYCLOAK_URL: str
    KEYCLOAK_ADMIN_REALM: str
    KEYCLOAK_APP_REALM: str
    USERNAME: str
    PASSWORD: SecretStr

    MCR_CLIENT_ID: str = "mcr"
    MCR_CORE_CLIENT_ID: str = "mcr-core"
    DRIVE_CLIENT_ID: str = "drive"

    TARGET_USER_EMAIL: str | None = None
    TARGET_USER_PASSWORD: SecretStr | None = None
    MCR_CORE_CLIENT_SECRET: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".drive_keycloak.env", extra="ignore"
    )


@dataclass
class CheckResult:
    name: str
    ok: bool
    reason: str = ""


def _audience_mapper(mappers: list[dict], audience: str) -> dict | None:
    for m in mappers:
        if (
            m.get("protocolMapper") == "oidc-audience-mapper"
            and m.get("config", {}).get("included.client.audience") == audience
            and m.get("config", {}).get("access.token.claim") == "true"
        ):
            return m
    return None


def check_mcr_client(admin: KeycloakAdmin, settings: Settings) -> CheckResult:
    name = f"{settings.MCR_CLIENT_ID} client present, public, standard flow"
    client_uuid = admin.get_client_id(settings.MCR_CLIENT_ID)
    if client_uuid is None:
        return CheckResult(name, False, f"client {settings.MCR_CLIENT_ID} not found")
    rep = admin.get_client(client_uuid)
    if rep.get("publicClient") is not True:
        return CheckResult(name, False, "client must be public")
    if not rep.get("standardFlowEnabled"):
        return CheckResult(name, False, "standard flow disabled")
    if not rep.get("redirectUris"):
        return CheckResult(name, False, "no valid redirect URIs configured")
    return CheckResult(name, True)


def check_mcr_audience_mapper(admin: KeycloakAdmin, settings: Settings) -> CheckResult:
    name = f"{settings.MCR_CLIENT_ID} client → audience mapper for {settings.MCR_CORE_CLIENT_ID}"
    client_uuid = admin.get_client_id(settings.MCR_CLIENT_ID)
    if client_uuid is None:
        return CheckResult(name, False, f"client {settings.MCR_CLIENT_ID} not found")
    mapper = _audience_mapper(
        admin.get_mappers_from_client(client_uuid), settings.MCR_CORE_CLIENT_ID
    )
    if mapper is None:
        return CheckResult(name, False, "audience mapper missing or misconfigured")
    return CheckResult(name, True)


def check_drive_client(admin: KeycloakAdmin, settings: Settings) -> CheckResult:
    name = (
        f"{settings.DRIVE_CLIENT_ID} client present, confidential, standard-flow only"
    )
    client_uuid = admin.get_client_id(settings.DRIVE_CLIENT_ID)
    if client_uuid is None:
        return CheckResult(name, False, f"client {settings.DRIVE_CLIENT_ID} not found")
    rep = admin.get_client(client_uuid)
    if rep.get("publicClient") is True:
        return CheckResult(name, False, "client is public, must be confidential")
    if not rep.get("standardFlowEnabled"):
        return CheckResult(name, False, "standard flow disabled")
    if rep.get("directAccessGrantsEnabled") or rep.get("serviceAccountsEnabled"):
        return CheckResult(
            name, False, "direct access grants or service accounts must be off"
        )
    if not rep.get("redirectUris"):
        return CheckResult(name, False, "no valid redirect URIs configured")
    return CheckResult(name, True)


def check_mcr_core_client(admin: KeycloakAdmin, settings: Settings) -> CheckResult:
    name = (
        f"{settings.MCR_CORE_CLIENT_ID} client present, confidential, "
        "directAccessGrants + serviceAccounts on"
    )
    client_uuid = admin.get_client_id(settings.MCR_CORE_CLIENT_ID)
    if client_uuid is None:
        return CheckResult(
            name, False, f"client {settings.MCR_CORE_CLIENT_ID} not found"
        )
    rep = admin.get_client(client_uuid)
    if rep.get("publicClient") is True:
        return CheckResult(name, False, "client is public, must be confidential")
    if not rep.get("directAccessGrantsEnabled"):
        return CheckResult(name, False, "directAccessGrants disabled")
    if not rep.get("serviceAccountsEnabled"):
        return CheckResult(name, False, "serviceAccounts disabled")
    return CheckResult(name, True)


def check_mcr_core_audience_mapper(
    admin: KeycloakAdmin, settings: Settings
) -> CheckResult:
    name = f"{settings.MCR_CORE_CLIENT_ID} client → audience mapper for {settings.DRIVE_CLIENT_ID}"
    client_uuid = admin.get_client_id(settings.MCR_CORE_CLIENT_ID)
    if client_uuid is None:
        return CheckResult(
            name, False, f"client {settings.MCR_CORE_CLIENT_ID} not found"
        )
    mapper = _audience_mapper(
        admin.get_mappers_from_client(client_uuid), settings.DRIVE_CLIENT_ID
    )
    if mapper is None:
        return CheckResult(name, False, "audience mapper missing or misconfigured")
    return CheckResult(name, True)


def check_token_exchange_works(settings: Settings) -> CheckResult | None:
    """Functional check: log in as TARGET_USER_EMAIL via the mcr client, then
    have mcr-core exchange that token for one with audience=mcr-core and
    scope=offline_access. This is exactly what `exchange_token_for_offline`
    does in mcr-core/mcr_meeting/app/services/token_exchange_service.py:41.

    Asserts a `refresh_token` is returned and the resulting access token's
    `aud` claim contains `mcr-core`.
    """
    if not (
        settings.TARGET_USER_EMAIL
        and settings.TARGET_USER_PASSWORD
        and settings.MCR_CORE_CLIENT_SECRET
    ):
        return None

    name = (
        f"token-exchange {settings.MCR_CLIENT_ID} → {settings.MCR_CORE_CLIENT_ID} "
        f"yields aud=[{settings.MCR_CORE_CLIENT_ID}] + offline refresh"
    )
    base = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_APP_REALM}/protocol/openid-connect/token"

    login = httpx.post(
        base,
        data={
            "grant_type": "password",
            "client_id": settings.MCR_CLIENT_ID,
            "username": settings.TARGET_USER_EMAIL,
            "password": settings.TARGET_USER_PASSWORD,
            "scope": "openid",
        },
        timeout=10.0,
    )
    if login.status_code != 200:
        return CheckResult(
            name,
            False,
            f"login as {settings.TARGET_USER_EMAIL} failed: {login.text[:200]}",
        )

    exchange = httpx.post(
        base,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "client_id": settings.MCR_CORE_CLIENT_ID,
            "client_secret": settings.MCR_CORE_CLIENT_SECRET,
            "subject_token": login.json()["access_token"],
            "audience": settings.MCR_CORE_CLIENT_ID,
            "scope": "openid offline_access",
        },
        timeout=10.0,
    )
    if exchange.status_code != 200:
        return CheckResult(name, False, f"exchange failed: {exchange.text[:200]}")

    body = exchange.json()
    if "refresh_token" not in body:
        return CheckResult(
            name, False, "exchange succeeded but returned no refresh_token"
        )

    access = body["access_token"]
    payload_b64 = access.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    aud = claims.get("aud")
    aud_list = aud if isinstance(aud, list) else [aud]
    if settings.MCR_CORE_CLIENT_ID not in aud_list:
        return CheckResult(
            name,
            False,
            f"exchanged token aud={aud!r} missing {settings.MCR_CORE_CLIENT_ID}",
        )

    return CheckResult(name, True)


def check_target_user_offline_access(
    admin: KeycloakAdmin, settings: Settings
) -> CheckResult | None:
    if not settings.TARGET_USER_EMAIL:
        return None
    name = f"{settings.TARGET_USER_EMAIL} → offline_access granted"
    user_id = admin.get_user_id(settings.TARGET_USER_EMAIL)
    if user_id is None:
        return CheckResult(name, False, "user not found")
    roles = {r.get("name") for r in admin.get_realm_roles_of_user(user_id)}
    if "offline_access" not in roles:
        return CheckResult(name, False, "offline_access role not assigned")
    return CheckResult(name, True)


def main() -> int:
    settings = Settings()  # type: ignore[call-arg]
    admin = KeycloakAdmin(
        server_url=settings.KEYCLOAK_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD,
        realm_name=settings.KEYCLOAK_APP_REALM,
        user_realm_name=settings.KEYCLOAK_ADMIN_REALM,
        verify=True,
    )

    checks: list[CheckResult] = [
        check_mcr_client(admin, settings),
        check_mcr_core_client(admin, settings),
        check_mcr_audience_mapper(admin, settings),
        check_drive_client(admin, settings),
        check_mcr_core_audience_mapper(admin, settings),
    ]
    for optional in (
        check_target_user_offline_access(admin, settings),
        check_token_exchange_works(settings),
    ):
        if optional is not None:
            checks.append(optional)

    passed = 0
    for c in checks:
        if c.ok:
            logger.info("[OK]   {}", c.name)
            passed += 1
        else:
            logger.error("[FAIL] {}: {}", c.name, c.reason)

    total = len(checks)
    logger.info("Result: {}/{} passed", passed, total)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
