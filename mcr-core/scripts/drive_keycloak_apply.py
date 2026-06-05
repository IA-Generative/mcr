"""Idempotent applier for the Drive Keycloak setup.

1. Create or update the `mcr` public frontend client.
2. Create or update the `mcr-core` confidential backend client.
3. Create or update the `drive` confidential client.
4. Ensure the `mcr-core-audience` mapper on the `mcr` client.
5. Ensure the `drive-audience` mapper on the `mcr-core` client.
6. Enable Admin Permissions on the `mcr-core` client, create the
   `mcr-token-exchange-policy` Client policy on `realm-management`, and
   attach it to the auto-generated `token-exchange.permission.client.<uuid>`.
7. Grant `offline_access` to each listed target user.

Each step is idempotent — re-running after a partial failure converges
to the correct state.

Run::

    cd mcr-core && uv run python scripts/drive_keycloak_apply.py
    cd mcr-core && uv run python scripts/drive_keycloak_apply.py --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakGetError
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
    REALM_MANAGEMENT_CLIENT_ID: str = "realm-management"
    TOKEN_EXCHANGE_POLICY_NAME: str = "mcr-token-exchange-policy"

    DRIVE_CLIENT_SECRET: SecretStr | None = None
    DRIVE_FRONTEND_BASE: str
    DRIVE_REDIRECT_URIS: list[str]
    DRIVE_WEB_ORIGINS: list[str] | None = None

    MCR_REDIRECT_URIS: list[str]
    MCR_WEB_ORIGINS: list[str] | None = None

    MCR_CORE_CLIENT_SECRET: SecretStr | None = None

    TARGET_USER_EMAILS: list[str] = []

    DRY_RUN: bool = False

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".drive_keycloak.env", extra="allow"
    )


STATE_CREATED = "created"
STATE_UPDATED = "updated"
STATE_ALREADY_CORRECT = "already correct"
STATE_DRY_RUN = "skipped (dry-run)"


def _audience_mapper_payload(name: str, audience: str) -> dict[str, object]:
    return {
        "name": name,
        "protocol": "openid-connect",
        "protocolMapper": "oidc-audience-mapper",
        "consentRequired": False,
        "config": {
            "included.client.audience": audience,
            "id.token.claim": "false",
            "access.token.claim": "true",
        },
    }


def apply_mcr_client(admin: KeycloakAdmin, settings: Settings) -> str:
    payload: dict[str, object] = {
        "clientId": settings.MCR_CLIENT_ID,
        "name": settings.MCR_CLIENT_ID,
        "description": "Frontend public client for MCR",
        "enabled": True,
        "redirectUris": settings.MCR_REDIRECT_URIS,
        "webOrigins": settings.MCR_WEB_ORIGINS or ["+"],
        "publicClient": True,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": False,
        "implicitFlowEnabled": False,
        "frontchannelLogout": True,
        "protocol": "openid-connect",
        "attributes": {
            "post.logout.redirect.uris": "+",
        },
        "fullScopeAllowed": True,
    }

    existing = admin.get_client_id(settings.MCR_CLIENT_ID)
    if existing is None:
        if settings.DRY_RUN:
            return STATE_DRY_RUN
        admin.create_client(payload)
        return STATE_CREATED

    current = admin.get_client(existing)
    if all(current.get(k) == v for k, v in payload.items()):
        return STATE_ALREADY_CORRECT
    if settings.DRY_RUN:
        return STATE_DRY_RUN
    admin.update_client(existing, payload)
    return STATE_UPDATED


def apply_mcr_core_client(admin: KeycloakAdmin, settings: Settings) -> str:
    payload: dict[str, object] = {
        "clientId": settings.MCR_CORE_CLIENT_ID,
        "name": settings.MCR_CORE_CLIENT_ID,
        "description": "Confidential client for mcr-core backend (token exchange)",
        "enabled": True,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["*"],
        "webOrigins": ["+"],
        "publicClient": False,
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": True,
        "implicitFlowEnabled": False,
        "frontchannelLogout": False,
        "protocol": "openid-connect",
        "fullScopeAllowed": True,
    }
    if settings.MCR_CORE_CLIENT_SECRET is not None:
        payload["secret"] = settings.MCR_CORE_CLIENT_SECRET.get_secret_value()

    existing = admin.get_client_id(settings.MCR_CORE_CLIENT_ID)
    if existing is None:
        if settings.DRY_RUN:
            return STATE_DRY_RUN
        admin.create_client(payload)
        return STATE_CREATED

    current = admin.get_client(existing)
    if all(current.get(k) == v for k, v in payload.items() if k != "secret"):
        return STATE_ALREADY_CORRECT
    if settings.DRY_RUN:
        return STATE_DRY_RUN
    admin.update_client(existing, payload)
    return STATE_UPDATED


def apply_drive_client(admin: KeycloakAdmin, settings: Settings) -> str:
    payload: dict[str, object] = {
        "clientId": settings.DRIVE_CLIENT_ID,
        "name": settings.DRIVE_CLIENT_ID,
        "description": "Confidential client for Drive integration",
        "enabled": True,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": settings.DRIVE_REDIRECT_URIS,
        "webOrigins": settings.DRIVE_WEB_ORIGINS or [settings.DRIVE_FRONTEND_BASE],
        "rootUrl": settings.DRIVE_FRONTEND_BASE,
        "publicClient": False,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "implicitFlowEnabled": False,
        "frontchannelLogout": True,
        "protocol": "openid-connect",
        "attributes": {
            "post.logout.redirect.uris": f"{settings.DRIVE_FRONTEND_BASE}/*",
        },
        "fullScopeAllowed": True,
    }
    if settings.DRIVE_CLIENT_SECRET is not None:
        payload["secret"] = settings.DRIVE_CLIENT_SECRET.get_secret_value()

    existing = admin.get_client_id(settings.DRIVE_CLIENT_ID)
    if existing is None:
        if settings.DRY_RUN:
            return STATE_DRY_RUN
        admin.create_client(payload)
        return STATE_CREATED

    current = admin.get_client(existing)
    if all(current.get(k) == v for k, v in payload.items() if k != "secret"):
        return STATE_ALREADY_CORRECT
    if settings.DRY_RUN:
        return STATE_DRY_RUN
    admin.update_client(existing, payload)
    return STATE_UPDATED


def apply_audience_mapper(
    admin: KeycloakAdmin,
    settings: Settings,
    *,
    on_client: str,
    mapper_name: str,
    audience: str,
) -> str:
    client_uuid = admin.get_client_id(on_client)
    if client_uuid is None:
        raise RuntimeError(f"client {on_client!r} not found in realm")

    mappers = admin.get_mappers_from_client(client_uuid)
    if any(m.get("name") == mapper_name for m in mappers):
        return STATE_ALREADY_CORRECT

    if settings.DRY_RUN:
        return STATE_DRY_RUN
    admin.add_mapper_to_client(
        client_uuid, _audience_mapper_payload(mapper_name, audience)
    )
    return STATE_CREATED


def apply_token_exchange_permission(admin: KeycloakAdmin, settings: Settings) -> str:
    mcr_uuid = admin.get_client_id(settings.MCR_CLIENT_ID)
    mcr_core_uuid = admin.get_client_id(settings.MCR_CORE_CLIENT_ID)
    realm_mgmt_uuid = admin.get_client_id(settings.REALM_MANAGEMENT_CLIENT_ID)
    if not (mcr_uuid and mcr_core_uuid and realm_mgmt_uuid):
        raise RuntimeError(
            "could not resolve mcr / mcr-core / realm-management client UUIDs"
        )

    changes: list[str] = []

    try:
        fgap_state = admin.get_client_management_permissions(mcr_core_uuid)
    except KeycloakGetError as e:
        if getattr(e, "response_code", None) == 501:
            logger.warning(
                "Keycloak returned 501 for client management permissions on "
                "{} — admin-fine-grained-authz / admin-permissions-v2 not "
                "enabled on this server. Skipping the optional token-exchange "
                "policy (internal-internal exchange works without it as long "
                "as the target client is confidential).",
                settings.MCR_CORE_CLIENT_ID,
            )
            return "skipped (server lacks admin-fine-grained-authz)"
        raise
    fgap_enabled = bool(fgap_state.get("enabled"))
    if not fgap_enabled:
        changes.append("fgap:enabled")
        if not settings.DRY_RUN:
            admin.update_client_management_permissions(
                {"enabled": True}, client_id=mcr_core_uuid
            )
            fgap_enabled = True

    if not fgap_enabled and settings.DRY_RUN:
        return STATE_DRY_RUN

    policies = admin.get_client_authz_policies(realm_mgmt_uuid)
    policy = next(
        (p for p in policies if p.get("name") == settings.TOKEN_EXCHANGE_POLICY_NAME),
        None,
    )
    if policy is None:
        if settings.DRY_RUN:
            changes.append("policy:created")
            policy_id = "<dry-run>"
        else:
            admin.create_client_authz_client_policy(
                {
                    "name": settings.TOKEN_EXCHANGE_POLICY_NAME,
                    "type": "client",
                    "logic": "POSITIVE",
                    "decisionStrategy": "UNANIMOUS",
                    "clients": [mcr_uuid],
                },
                client_id=realm_mgmt_uuid,
            )
            policy = next(
                p
                for p in admin.get_client_authz_policies(realm_mgmt_uuid)
                if p.get("name") == settings.TOKEN_EXCHANGE_POLICY_NAME
            )
            policy_id = policy["id"]
            changes.append("policy:created")
    else:
        policy_id = policy["id"]

    permissions = admin.get_client_authz_permissions(realm_mgmt_uuid)
    expected_name = f"token-exchange.permission.client.{mcr_core_uuid}"
    permission = next((p for p in permissions if p.get("name") == expected_name), None)
    if permission is None:
        raise RuntimeError(
            f"permission {expected_name} not found — "
            f"enabling Admin Permissions on {settings.MCR_CORE_CLIENT_ID} did not create it; "
            "verify Keycloak >= 26.0 and the client is confidential"
        )

    associated = admin.get_client_authz_permission_associated_policies(
        realm_mgmt_uuid, permission["id"]
    )
    if not any(p.get("id") == policy_id for p in associated):
        if settings.DRY_RUN:
            changes.append("permission:linked")
        else:
            new_policy_ids = [p["id"] for p in associated] + [policy_id]
            admin.update_client_authz_scope_permission(
                payload={
                    "id": permission["id"],
                    "name": permission["name"],
                    "type": permission["type"],
                    "logic": permission.get("logic", "POSITIVE"),
                    "decisionStrategy": permission.get("decisionStrategy", "UNANIMOUS"),
                    "resources": permission.get("resources", []),
                    "scopes": permission.get("scopes", []),
                    "policies": new_policy_ids,
                },
                client_id=realm_mgmt_uuid,
                scope_id=permission["id"],
            )
            changes.append("permission:linked")

    if not changes:
        return STATE_ALREADY_CORRECT
    if settings.DRY_RUN:
        return STATE_DRY_RUN
    return f"applied ({', '.join(changes)})"


def apply_offline_access(admin: KeycloakAdmin, settings: Settings) -> str:
    if not settings.TARGET_USER_EMAILS:
        return STATE_ALREADY_CORRECT

    role = admin.get_realm_role("offline_access")
    changed = 0
    skipped = 0
    for email in settings.TARGET_USER_EMAILS:
        user_id = admin.get_user_id(email)
        if user_id is None:
            logger.warning("user {} not found, skipping", email)
            skipped += 1
            continue
        current = {r.get("name") for r in admin.get_realm_roles_of_user(user_id)}
        if "offline_access" in current:
            continue
        if settings.DRY_RUN:
            changed += 1
            continue
        admin.assign_realm_roles(user_id, [role])
        changed += 1

    if changed == 0:
        return STATE_ALREADY_CORRECT
    if settings.DRY_RUN:
        return STATE_DRY_RUN
    return f"granted to {changed} user(s), {skipped} skipped"


def main() -> int:
    cli_dry_run = "--dry-run" in sys.argv[1:]
    settings = Settings()  # type: ignore[call-arg]
    if cli_dry_run:
        settings = settings.model_copy(update={"DRY_RUN": True})

    if settings.DRY_RUN:
        logger.warning("DRY-RUN: no admin API writes will be issued")

    admin = KeycloakAdmin(
        server_url=settings.KEYCLOAK_URL,
        username=settings.USERNAME,
        password=settings.PASSWORD.get_secret_value(),
        realm_name=settings.KEYCLOAK_APP_REALM,
        user_realm_name=settings.KEYCLOAK_ADMIN_REALM,
        verify=True,
    )

    steps: list[tuple[str, str]] = []

    try:
        steps.append(("mcr client", apply_mcr_client(admin, settings)))
        steps.append(("mcr-core client", apply_mcr_core_client(admin, settings)))
        steps.append(("drive client", apply_drive_client(admin, settings)))
        steps.append(
            (
                "mcr-core-audience mapper on mcr",
                apply_audience_mapper(
                    admin,
                    settings,
                    on_client=settings.MCR_CLIENT_ID,
                    mapper_name="mcr-core-audience",
                    audience=settings.MCR_CORE_CLIENT_ID,
                ),
            )
        )
        steps.append(
            (
                "drive-audience mapper on mcr-core",
                apply_audience_mapper(
                    admin,
                    settings,
                    on_client=settings.MCR_CORE_CLIENT_ID,
                    mapper_name="drive-audience",
                    audience=settings.DRIVE_CLIENT_ID,
                ),
            )
        )
        steps.append(
            (
                "token-exchange permission on mcr-core",
                apply_token_exchange_permission(admin, settings),
            )
        )
        steps.append(("offline_access role", apply_offline_access(admin, settings)))
    except Exception as e:
        logger.exception("apply failed: {}", e)
        for name, state in steps:
            logger.info("[apply] {}: {}", name, state)
        return 1

    for name, state in steps:
        logger.info("[apply] {}: {}", name, state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
