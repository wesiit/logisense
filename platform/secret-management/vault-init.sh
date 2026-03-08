#!/usr/bin/env bash
# ==============================================================================
# LogiSense Vault Initialization Script
# ==============================================================================
# Initializes Vault with secrets engines, policies, and dev secrets.
# Uses Vault HTTP API (no vault CLI required).
# ==============================================================================
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-root-token}"

# PostgreSQL connection details
PG_HOST="${PG_HOST:-postgres}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-logisense}"
PG_PASSWORD="${PG_PASSWORD:-logisense_dev}"
PG_DATABASE="${PG_DATABASE:-logisense}"

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                    LogiSense Vault Initialization                        ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Vault Address: $VAULT_ADDR"
echo ""

# Helper function for Vault API calls
vault_api() {
    local method="$1"
    local path="$2"
    local data="${3:-}"

    if [ -n "$data" ]; then
        curl -sf -X "$method" \
            -H "X-Vault-Token: $VAULT_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "${VAULT_ADDR}/v1/${path}"
    else
        curl -sf -X "$method" \
            -H "X-Vault-Token: $VAULT_TOKEN" \
            "${VAULT_ADDR}/v1/${path}"
    fi
}

# Wait for Vault to be ready
echo "Waiting for Vault to be healthy..."
until curl -sf "${VAULT_ADDR}/v1/sys/health" > /dev/null 2>&1; do
    sleep 2
done
echo "✓ Vault is ready"
echo ""

# ==============================================================================
# Enable KV v2 Secrets Engine
# ==============================================================================
echo "Enabling KV v2 secrets engine at logisense/..."
vault_api POST "sys/mounts/logisense" '{"type":"kv","options":{"version":"2"}}' 2>/dev/null || \
    echo "  (already enabled)"
echo "✓ KV v2 secrets engine enabled"

# ==============================================================================
# Enable Database Secrets Engine
# ==============================================================================
echo "Enabling database secrets engine..."
vault_api POST "sys/mounts/database" '{"type":"database"}' 2>/dev/null || \
    echo "  (already enabled)"
echo "✓ Database secrets engine enabled"

# ==============================================================================
# Configure PostgreSQL Database Connection
# ==============================================================================
echo "Configuring PostgreSQL connection..."
vault_api POST "database/config/logisense-postgres" "{
    \"plugin_name\": \"postgresql-database-plugin\",
    \"allowed_roles\": [\"logisense-app\"],
    \"connection_url\": \"postgresql://{{username}}:{{password}}@${PG_HOST}:${PG_PORT}/${PG_DATABASE}?sslmode=disable\",
    \"username\": \"${PG_USER}\",
    \"password\": \"${PG_PASSWORD}\"
}" > /dev/null
echo "✓ PostgreSQL connection configured"

# ==============================================================================
# Create PostgreSQL Dynamic Credentials Role
# ==============================================================================
echo "Creating PostgreSQL dynamic credentials role 'logisense-app'..."

CREATION_SQL='CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '"'"'{{password}}'"'"' VALID UNTIL '"'"'{{expiration}}'"'"';
GRANT USAGE ON SCHEMA iwms TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA iwms TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA iwms TO \"{{name}}\";
GRANT USAGE ON SCHEMA lip TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA lip TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA lip TO \"{{name}}\";
GRANT USAGE ON SCHEMA ccvp TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ccvp TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ccvp TO \"{{name}}\";
GRANT USAGE ON SCHEMA pise TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA pise TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA pise TO \"{{name}}\";
GRANT USAGE ON SCHEMA wcvp TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA wcvp TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA wcvp TO \"{{name}}\";
GRANT USAGE ON SCHEMA uoih TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA uoih TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA uoih TO \"{{name}}\";
GRANT USAGE ON SCHEMA license TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA license TO \"{{name}}\";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA license TO \"{{name}}\";'

REVOCATION_SQL='REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA iwms FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA iwms FROM \"{{name}}\";
REVOKE USAGE ON SCHEMA iwms FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA lip FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA lip FROM \"{{name}}\";
REVOKE USAGE ON SCHEMA lip FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA ccvp FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ccvp FROM \"{{name}}\";
REVOKE USAGE ON SCHEMA ccvp FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA pise FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA pise FROM \"{{name}}\";
REVOKE USAGE ON SCHEMA pise FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA wcvp FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA wcvp FROM \"{{name}}\";
REVOKE USAGE ON SCHEMA wcvp FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA uoih FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA uoih FROM \"{{name}}\";
REVOKE USAGE ON SCHEMA uoih FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA license FROM \"{{name}}\";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA license FROM \"{{name}}\";
REVOKE USAGE ON SCHEMA license FROM \"{{name}}\";
DROP ROLE IF EXISTS \"{{name}}\";'

# Use jq-free JSON construction
vault_api POST "database/roles/logisense-app" "$(cat <<EOF
{
    "db_name": "logisense-postgres",
    "creation_statements": ["$(echo "$CREATION_SQL" | tr '\n' ' ')"],
    "revocation_statements": ["$(echo "$REVOCATION_SQL" | tr '\n' ' ')"],
    "default_ttl": "1h",
    "max_ttl": "24h"
}
EOF
)" > /dev/null
echo "✓ PostgreSQL dynamic credentials role created"

# ==============================================================================
# Write Static Dev Secrets
# ==============================================================================
echo "Writing static dev secrets..."

# Kafka secrets
vault_api POST "logisense/data/dev/kafka" '{
    "data": {
        "bootstrap_servers": "kafka:9092"
    }
}' > /dev/null
echo "  ✓ logisense/dev/kafka"

# MinIO secrets (pragma: allowlist secret)
vault_api POST "logisense/data/dev/minio" '{
    "data": {
        "endpoint": "http://minio:9000",
        "access_key": "minioadmin",
        "secret_key": "minioadmin123"
    }
}' > /dev/null
echo "  ✓ logisense/dev/minio"

# Keycloak secrets (pragma: allowlist secret)
vault_api POST "logisense/data/dev/keycloak" '{
    "data": {
        "server_url": "http://keycloak:8080",
        "realm": "logisense",
        "client_id": "logisense-api",
        "client_secret": "logisense-api-secret-dev"
    }
}' > /dev/null
echo "  ✓ logisense/dev/keycloak"

# Redis secrets
vault_api POST "logisense/data/dev/redis" '{
    "data": {
        "host": "redis",
        "port": "6379",
        "url": "redis://redis:6379"
    }
}' > /dev/null
echo "  ✓ logisense/dev/redis"

# ==============================================================================
# Create Vault Policy
# ==============================================================================
echo "Creating Vault policy 'logisense-app-policy'..."

POLICY='path "logisense/data/dev/*" {
  capabilities = ["read", "list"]
}
path "logisense/metadata/dev/*" {
  capabilities = ["read", "list"]
}
path "database/creds/logisense-app" {
  capabilities = ["read"]
}
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
path "auth/token/renew-self" {
  capabilities = ["update"]
}'

vault_api PUT "sys/policies/acl/logisense-app-policy" "{
    \"policy\": $(echo "$POLICY" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
}" > /dev/null
echo "✓ Vault policy created"

# ==============================================================================
# Enable AppRole Auth Method
# ==============================================================================
echo "Enabling AppRole auth method..."
vault_api POST "sys/auth/approle" '{"type":"approle"}' 2>/dev/null || \
    echo "  (already enabled)"
echo "✓ AppRole auth method enabled"

# ==============================================================================
# Create AppRole Role
# ==============================================================================
echo "Creating AppRole role 'logisense-app'..."
vault_api POST "auth/approle/role/logisense-app" '{
    "token_policies": ["logisense-app-policy"],
    "token_ttl": "1h",
    "token_max_ttl": "4h",
    "secret_id_ttl": "720h",
    "secret_id_num_uses": 0
}' > /dev/null
echo "✓ AppRole role created"

# Get Role ID
ROLE_ID=$(curl -sf -H "X-Vault-Token: $VAULT_TOKEN" \
    "${VAULT_ADDR}/v1/auth/approle/role/logisense-app/role-id" | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['data']['role_id'])")

# Generate Secret ID
SECRET_ID=$(curl -sf -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    "${VAULT_ADDR}/v1/auth/approle/role/logisense-app/secret-id" | \
    python3 -c "import sys,json; print(json.load(sys.stdin)['data']['secret_id'])")

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                    Vault Initialization Complete                         ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
echo "║  AppRole Credentials (save these for application use):                   ║"
echo "╠──────────────────────────────────────────────────────────────────────────╣"
printf "║  Role ID:   %-60s ║\n" "$ROLE_ID"
printf "║  Secret ID: %-60s ║\n" "$SECRET_ID"
echo "╠──────────────────────────────────────────────────────────────────────────╣"
echo "║  Secret Paths:                                                           ║"
echo "║    logisense/dev/kafka                                                   ║"
echo "║    logisense/dev/minio                                                   ║"
echo "║    logisense/dev/keycloak                                                ║"
echo "║    logisense/dev/redis                                                   ║"
echo "║    database/creds/logisense-app (dynamic)                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Test with:"
echo "  curl -s -H 'X-Vault-Token: $VAULT_TOKEN' ${VAULT_ADDR}/v1/logisense/data/dev/kafka | python3 -m json.tool"
