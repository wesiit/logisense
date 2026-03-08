#!/usr/bin/env bash
# ==============================================================================
# LogiSense Vault Status Script
# ==============================================================================
# Checks Vault health and prints all configured secret paths.
# Uses Vault HTTP API (no vault CLI required).
# ==============================================================================
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-root-token}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                        LogiSense Vault Status                            ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
printf "Vault Address: %s\n" "$VAULT_ADDR"
echo ""

# Helper function for Vault API calls
vault_get() {
    local path="$1"
    curl -sf -H "X-Vault-Token: $VAULT_TOKEN" "${VAULT_ADDR}/v1/${path}" 2>/dev/null
}

# ==============================================================================
# Health Check
# ==============================================================================
echo -e "${BLUE}Checking Vault health...${NC}"

HEALTH_RESPONSE=$(curl -s "${VAULT_ADDR}/v1/sys/health" 2>/dev/null || echo '{"error":"connection failed"}')

if echo "$HEALTH_RESPONSE" | grep -q '"initialized":true'; then
    echo -e "${GREEN}✓ Vault is initialized${NC}"
else
    echo -e "${RED}✗ Vault is not initialized or unreachable${NC}"
    exit 1
fi

if echo "$HEALTH_RESPONSE" | grep -q '"sealed":false'; then
    echo -e "${GREEN}✓ Vault is unsealed${NC}"
else
    echo -e "${RED}✗ Vault is sealed${NC}"
    exit 1
fi

if echo "$HEALTH_RESPONSE" | grep -q '"standby":false'; then
    echo -e "${GREEN}✓ Vault is active (not standby)${NC}"
fi

echo ""

# ==============================================================================
# Secrets Engines
# ==============================================================================
echo -e "${BLUE}Secrets Engines:${NC}"

MOUNTS=$(vault_get "sys/mounts" 2>/dev/null || echo '{}')

if echo "$MOUNTS" | grep -q '"logisense/"'; then
    echo -e "  ${GREEN}✓${NC} logisense/ (kv-v2)"
else
    echo -e "  ${YELLOW}○${NC} logisense/ (not mounted)"
fi

if echo "$MOUNTS" | grep -q '"database/"'; then
    echo -e "  ${GREEN}✓${NC} database/"
else
    echo -e "  ${YELLOW}○${NC} database/ (not mounted)"
fi

echo ""

# ==============================================================================
# Static Secrets
# ==============================================================================
echo -e "${BLUE}Static Secrets (logisense/dev/):${NC}"

for secret in kafka minio keycloak redis; do
    RESPONSE=$(vault_get "logisense/data/dev/${secret}" 2>/dev/null || echo '{"errors":["not found"]}')

    if echo "$RESPONSE" | grep -q '"data"'; then
        echo -e "  ${GREEN}✓${NC} logisense/dev/${secret}"
        KEYS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}).get('data',{}); print('    Keys:', ', '.join(d.keys()))" 2>/dev/null || echo "")
        [ -n "$KEYS" ] && echo "$KEYS"
    else
        echo -e "  ${RED}✗${NC} logisense/dev/${secret} (not found)"
    fi
done
echo ""

# ==============================================================================
# Database Secrets Engine
# ==============================================================================
echo -e "${BLUE}Database Secrets Engine:${NC}"

DB_CONFIG=$(vault_get "database/config/logisense-postgres" 2>/dev/null || echo '{}')
if echo "$DB_CONFIG" | grep -q '"connection_details"'; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL connection configured"
else
    echo -e "  ${YELLOW}○${NC} PostgreSQL connection not configured"
fi

DB_ROLE=$(vault_get "database/roles/logisense-app" 2>/dev/null || echo '{}')
if echo "$DB_ROLE" | grep -q '"db_name"'; then
    echo -e "  ${GREEN}✓${NC} Dynamic role 'logisense-app' configured"
    TTL=$(echo "$DB_ROLE" | python3 -c "import sys,json; print('Default TTL:', json.load(sys.stdin).get('data',{}).get('default_ttl','unknown'))" 2>/dev/null || echo "")
    [ -n "$TTL" ] && echo "    $TTL"
else
    echo -e "  ${YELLOW}○${NC} Dynamic role 'logisense-app' not configured"
fi
echo ""

# ==============================================================================
# Auth Methods
# ==============================================================================
echo -e "${BLUE}Auth Methods:${NC}"

AUTH_METHODS=$(vault_get "sys/auth" 2>/dev/null || echo '{}')

if echo "$AUTH_METHODS" | grep -q '"approle/"'; then
    echo -e "  ${GREEN}✓${NC} approle/"
else
    echo -e "  ${YELLOW}○${NC} approle/ (not enabled)"
fi

echo ""

# ==============================================================================
# Policies
# ==============================================================================
echo -e "${BLUE}Policies:${NC}"

POLICY=$(vault_get "sys/policies/acl/logisense-app-policy" 2>/dev/null || echo '{}')
if echo "$POLICY" | grep -q '"policy"'; then
    echo -e "  ${GREEN}✓${NC} logisense-app-policy"
else
    echo -e "  ${YELLOW}○${NC} logisense-app-policy (not found)"
fi
echo ""

# ==============================================================================
# AppRole
# ==============================================================================
echo -e "${BLUE}AppRole:${NC}"

APPROLE=$(vault_get "auth/approle/role/logisense-app" 2>/dev/null || echo '{}')
if echo "$APPROLE" | grep -q '"token_policies"'; then
    echo -e "  ${GREEN}✓${NC} Role 'logisense-app' configured"
    ROLE_ID_RESP=$(vault_get "auth/approle/role/logisense-app/role-id" 2>/dev/null || echo '{}')
    ROLE_ID=$(echo "$ROLE_ID_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('role_id','unknown'))" 2>/dev/null || echo "unknown")
    echo "    Role ID: ${ROLE_ID}"
else
    echo -e "  ${YELLOW}○${NC} Role 'logisense-app' not configured"
fi
echo ""

# ==============================================================================
# Test Dynamic Credentials
# ==============================================================================
echo -e "${BLUE}Testing Dynamic Credentials:${NC}"
echo "  Generating temporary PostgreSQL credentials..."

DB_CREDS=$(vault_get "database/creds/logisense-app" 2>/dev/null || echo '{"errors":["failed"]}')

if echo "$DB_CREDS" | grep -q '"username"'; then
    USERNAME=$(echo "$DB_CREDS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['username'])")
    LEASE_ID=$(echo "$DB_CREDS" | python3 -c "import sys,json; print(json.load(sys.stdin)['lease_id'])")
    TTL=$(echo "$DB_CREDS" | python3 -c "import sys,json; print(json.load(sys.stdin)['lease_duration'])")
    echo -e "  ${GREEN}✓${NC} Dynamic credentials generated"
    echo "    Username: ${USERNAME}"
    echo "    TTL: ${TTL}s"
    echo "    Lease ID: ${LEASE_ID:0:40}..."

    # Revoke the test credentials
    curl -sf -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
        -d "{\"lease_id\":\"$LEASE_ID\"}" \
        "${VAULT_ADDR}/v1/sys/leases/revoke" > /dev/null 2>&1 || true
    echo "    (credentials revoked after test)"
else
    echo -e "  ${YELLOW}○${NC} Could not generate dynamic credentials"
    echo "    This may be expected if PostgreSQL is not running or reachable from Vault"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                          Status Check Complete                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
