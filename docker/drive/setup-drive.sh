#!/usr/bin/env bash
# One-time idempotent setup for Drive integration alongside MCR.
# Run via: make init-drive
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCR_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
DRIVE_DIR="$MCR_DIR/../drive"

# Pinned Drive version — update when upgrading Drive
DRIVE_VERSION="feb82b2"

# ── 1. Check Drive repo exists ──────────────────────────────────────────────
if [ ! -d "$DRIVE_DIR" ]; then
  echo "ERROR: Drive repo not found at $DRIVE_DIR"
  echo "Clone it first at https://github.com/suitenumerique/drive, then re-run this script."
  exit 1
fi

# ── 1b. Pin Drive to tested version ────────────────────────────────────────
echo "Checking out Drive at $DRIVE_VERSION..."
cd "$DRIVE_DIR" && git checkout "$DRIVE_VERSION" --quiet
cd "$MCR_DIR"

# ── 2. Create shared Docker network (idempotent) ───────────────────────────
docker network create shared-network 2>/dev/null || true

# ── 3. Create Drive env files & patch OIDC config ─────────────────────────
cd "$DRIVE_DIR"
make create-env-local-files
cd "$MCR_DIR"

DRIVE_COMMON_LOCAL="$DRIVE_DIR/env.d/development/common.local"

write_or_replace() {
  local key="$1" val="$2" file="$3"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$file" && rm -f "${file}.bak"
  else
    echo "${key}=${val}" >> "$file"
  fi
}

write_or_replace "OIDC_OP_URL" "http://localhost:8083/realms/mirai" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_OP_JWKS_ENDPOINT" "http://nginx:8083/realms/mirai/protocol/openid-connect/certs" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_OP_AUTHORIZATION_ENDPOINT" "http://localhost:8083/realms/mirai/protocol/openid-connect/auth" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_OP_TOKEN_ENDPOINT" "http://nginx:8083/realms/mirai/protocol/openid-connect/token" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_OP_USER_ENDPOINT" "http://nginx:8083/realms/mirai/protocol/openid-connect/userinfo" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_OP_INTROSPECTION_ENDPOINT" "http://nginx:8083/realms/mirai/protocol/openid-connect/token/introspect" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_RP_CLIENT_ID" "drive" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_RP_CLIENT_SECRET" "drive-local-secret" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_RP_SIGN_ALGO" "RS256" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_RESOURCE_SERVER_ENABLED" "True" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_RS_CLIENT_ID" "drive" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_RS_CLIENT_SECRET" "drive-local-secret" "$DRIVE_COMMON_LOCAL"
write_or_replace "OIDC_RS_ALLOWED_AUDIENCES" '"mcr,mcr-gateway,mcr-core"' "$DRIVE_COMMON_LOCAL"
write_or_replace "AWS_S3_DOMAIN_REPLACE" "http://drive-minio:9000" "$DRIVE_COMMON_LOCAL"

echo "Drive env configured."

# ── 4. Patch nginx config (point Keycloak proxy at MCR's Keycloak) ────────
NGINX_CONF="$DRIVE_DIR/docker/files/development/etc/nginx/conf.d/default.conf"
if [ -f "$NGINX_CONF" ] && ! grep -q 'mcr-keycloak' "$NGINX_CONF"; then
  sed -i.bak \
    's|proxy_pass http://keycloak:8080;|proxy_pass http://mcr-keycloak:8083;|' \
    "$NGINX_CONF" && rm -f "${NGINX_CONF}.bak"
  echo "Patched nginx config (Keycloak proxy → MCR)"
else
  echo "Nginx config already patched or not found, skipping"
fi

# ── 5. Copy compose overrides ───────────────────────────────────────────────
# MCR override: adds shared-network to keycloak + mcr-core
MCR_OVERRIDE_DST="$MCR_DIR/docker-compose.override.yml"
if [ ! -f "$MCR_OVERRIDE_DST" ]; then
  cp "$SCRIPT_DIR/docker-compose.override.yml.mcr" "$MCR_OVERRIDE_DST"
  echo "Copied MCR docker-compose.override.yml"
else
  echo "MCR docker-compose.override.yml already exists, skipping copy"
fi

# Drive override: remaps ports, disables Drive's Keycloak, adds shared-network
DRIVE_OVERRIDE_DST="$DRIVE_DIR/compose.override.yml"
if [ ! -f "$DRIVE_OVERRIDE_DST" ]; then
  cp "$SCRIPT_DIR/compose.override.yml.drive" "$DRIVE_OVERRIDE_DST"
  echo "Copied Drive compose.override.yml"
else
  echo "Drive compose.override.yml already exists, skipping copy"
fi

# ── 6. Ensure MCR .env has Drive vars ───────────────────────────────────────
MCR_ENV="$MCR_DIR/.env"
touch "$MCR_ENV"

write_or_replace "KEYCLOAK_CORE_CLIENT_ID" "mcr-core" "$MCR_ENV"
write_or_replace "KEYCLOAK_CORE_CLIENT_SECRET" "mcr-core-local-secret" "$MCR_ENV"
write_or_replace "DRIVE_API_BASE_URL" "http://app-dev:8000" "$MCR_ENV"
write_or_replace "DRIVE_FRONTEND_URL" "http://localhost:3000" "$MCR_ENV"
write_or_replace "VITE_DRIVE_URL" "http://localhost:3000" "$MCR_ENV"

echo "MCR .env configured."

# ── 7. Build Drive images ───────────────────────────────────────────────────
echo "Building Drive images..."
cd "$DRIVE_DIR"
docker compose build app-dev celery-dev

echo ""
echo "Drive setup complete. Run 'make start-drive' to start both stacks."
