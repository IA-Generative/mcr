#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$SCRIPT_DIR/require.sh"

require vault "https://developer.hashicorp.com/vault/install"

if [ -z "${VAULT_ADDR:-}" ]; then
  echo "ERROR: VAULT_ADDR is not set." >&2
  echo "  export VAULT_ADDR=https://your.vault.com" >&2
  exit 1
fi

if ! vault token lookup >/dev/null 2>&1; then
  echo "Not authenticated to Vault. Logging in..."
  vault login -method=oidc -path=oidc role=default
fi

# Resolve ~ in vault-agent.hcl (HCL doesn't expand it)
AGENT_CONFIG=$(mktemp)
sed -e "s|__VAULT_TOKEN_PATH__|$HOME/.vault-token|" \
    -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
    "$PROJECT_ROOT/vault-agent.hcl" > "$AGENT_CONFIG"
trap "rm -f $AGENT_CONFIG" EXIT

vault agent -config="$AGENT_CONFIG" -exit-after-auth

KEY_COUNT=$(grep -cE '^[A-Za-z_]' "$PROJECT_ROOT/.env" 2>/dev/null || echo 0)
echo "sync-env: .env updated ($KEY_COUNT keys from Vault)"
