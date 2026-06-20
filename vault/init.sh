#!/bin/sh
set -e

INIT_FILE="/vault/init/keys.json"

# Check if vault is already initialized
VAULT_STATUS=$(vault status 2>/dev/null || true)

if echo "$VAULT_STATUS" | grep -q "Initialized.*true"; then
    echo "Vault already initialized"

    if echo "$VAULT_STATUS" | grep -q "Sealed.*true"; then
        echo "Vault is sealed — unsealing..."
        if [ ! -f "$INIT_FILE" ]; then
            echo "ERROR: Vault is sealed but $INIT_FILE is missing. Delete the vault_data volume and restart." >&2
            exit 1
        fi
        # Extract unseal key — handle both compact and pretty-printed JSON
        UNSEAL_KEY=$(grep -A1 'unseal_keys_b64' "$INIT_FILE" | tail -1 | tr -d ' [],\"')
        vault operator unseal "$UNSEAL_KEY"
        echo "Vault unsealed"
    fi

    exit 0
fi

echo "First boot — initializing Vault..."
mkdir -p /vault/init

vault operator init -key-shares=1 -key-threshold=1 -format=json > "$INIT_FILE"

# Extract from pretty-printed JSON
UNSEAL_KEY=$(grep -A1 'unseal_keys_b64' "$INIT_FILE" | tail -1 | tr -d ' [],\"')
ROOT_TOKEN=$(grep '"root_token"' "$INIT_FILE" | sed 's/.*: *//' | tr -d ' ",')

vault operator unseal "$UNSEAL_KEY"

export VAULT_TOKEN="$ROOT_TOKEN"

# Create a stable well-known token so VAULT_TOKEN=dev-root-token still works everywhere
vault token create -id=dev-root-token -policy=root -orphan -period=87600h > /dev/null

vault secrets enable -path=secret kv-v2

vault kv put secret/dealroom/auth        secret_key=changeme-min-32-chars-local-dev
vault kv put secret/dealroom/database    url=postgresql+asyncpg://dealroom:password@db:5432/dealroom
vault kv put secret/dealroom/redis       url=redis://redis:6379/0
vault kv put secret/dealroom/openai      api_key=sk-replace-me
vault kv put secret/dealroom/langsmith   api_key=ls-replace-me
vault kv put secret/dealroom/minio       access_key=minioadmin secret_key=minioadmin
vault kv put secret/dealroom/email       smtp_password=replace-me
vault kv put secret/dealroom/research    tavily_key=replace-me news_api_key=replace-me alpha_vantage_key=replace-me

echo "Vault seeded. Update real values once with: docker exec dealroom_vault sh -c \"VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=dev-root-token vault kv patch secret/dealroom/<path> <key>=<value>\""
