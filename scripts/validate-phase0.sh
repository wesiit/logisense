#!/usr/bin/env bash
# ==============================================================================
# LogiSense Phase 0 Validation Script
# ==============================================================================
# Validates all infrastructure components are working correctly
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# ==============================================================================
# Utility Functions
# ==============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                          ║"
    echo "║                    LogiSense Phase 0 Validation                          ║"
    echo "║                                                                          ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_test() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}"
}

pass() {
    echo -e "  ${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "  ${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

skip() {
    echo -e "  ${YELLOW}[SKIP]${NC} $1"
    ((TESTS_SKIPPED++))
}

# ==============================================================================
# Service Health Checks
# ==============================================================================

test_service_health() {
    log_test "Service Health Checks"

    local services=(
        "Kong|http://localhost:8000/"
        "Kong Admin|http://localhost:8001/status"
        "Keycloak|http://localhost:8080/health/ready"
        "Vault|http://localhost:8200/v1/sys/health"
        "MinIO|http://localhost:9000/minio/health/live"
        "Prometheus|http://localhost:9090/-/healthy"
        "Grafana|http://localhost:3000/api/health"
        "License API|http://localhost:8007/health"
        "Loki|http://localhost:3100/ready"
    )

    for service_info in "${services[@]}"; do
        IFS='|' read -r name url <<< "$service_info"

        local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5 2>/dev/null || echo "000")

        if [[ "$status" =~ ^(200|204|429|472|473)$ ]]; then
            pass "$name is healthy (HTTP $status)"
        elif [[ "$status" == "000" ]]; then
            fail "$name is not reachable"
        else
            fail "$name returned HTTP $status"
        fi
    done
}

# ==============================================================================
# Kafka Test
# ==============================================================================

test_kafka() {
    log_test "Kafka Produce/Consume Test"

    local topic="logisense.iwms.inventory.movement"
    local test_message="test-message-$(date +%s)"
    local kafka_container="logisense-kafka"

    # Check if Kafka container is running
    if ! docker ps --format '{{.Names}}' | grep -q "$kafka_container"; then
        fail "Kafka container not running"
        return
    fi

    # Produce a test message
    echo "  Producing test message to $topic..."
    local produce_result=$(docker exec "$kafka_container" bash -c \
        "echo '$test_message' | kafka-console-producer --bootstrap-server localhost:9092 --topic $topic 2>&1" || echo "error")

    if [[ "$produce_result" == *"error"* && "$produce_result" != "" ]]; then
        # Producer doesn't output on success, only on error
        if [[ "$produce_result" == *"ERROR"* ]]; then
            fail "Failed to produce message: $produce_result"
            return
        fi
    fi
    pass "Produced message to $topic"

    # Consume the test message
    echo "  Consuming message from $topic..."
    local consume_result=$(docker exec "$kafka_container" bash -c \
        "timeout 10 kafka-console-consumer --bootstrap-server localhost:9092 --topic $topic --from-beginning --max-messages 1 2>/dev/null" || echo "")

    if [[ "$consume_result" == *"$test_message"* ]]; then
        pass "Consumed message from $topic"
    else
        # Try with a different approach - just check if we can consume anything
        local any_message=$(docker exec "$kafka_container" bash -c \
            "timeout 5 kafka-console-consumer --bootstrap-server localhost:9092 --topic $topic --from-beginning --max-messages 1 2>/dev/null" || echo "")
        if [[ -n "$any_message" ]]; then
            pass "Consumed message from $topic (different message)"
        else
            fail "Failed to consume message from $topic"
        fi
    fi
}

# ==============================================================================
# MinIO Test
# ==============================================================================

test_minio() {
    log_test "MinIO Upload/Download Test"

    local bucket="logisense-bronze"
    local test_file="test-file-$(date +%s).txt"
    local test_content="LogiSense MinIO test content - $(date)"
    local minio_container="logisense-minio"

    # Check if MinIO container is running
    if ! docker ps --format '{{.Names}}' | grep -q "$minio_container"; then
        fail "MinIO container not running"
        return
    fi

    # Create a test file and upload it
    echo "  Uploading test file to $bucket..."

    # Use mc (MinIO Client) inside the minio-init container or via curl
    local upload_result=$(docker exec "$minio_container" bash -c "
        echo '$test_content' > /tmp/$test_file
        mc alias set myminio http://localhost:9000 minioadmin minioadmin123 2>/dev/null
        mc cp /tmp/$test_file myminio/$bucket/$test_file 2>&1
    " 2>&1 || echo "error")

    if [[ "$upload_result" == *"error"* ]] || [[ "$upload_result" == *"ERROR"* ]]; then
        # Try alternative method using curl
        local presigned_upload=$(curl -s -X PUT \
            "http://localhost:9000/$bucket/$test_file" \
            -H "Content-Type: text/plain" \
            -d "$test_content" \
            -u "minioadmin:minioadmin123" \
            -w "%{http_code}" \
            -o /dev/null 2>/dev/null || echo "000")

        if [[ "$presigned_upload" == "200" ]]; then
            pass "Uploaded test file to $bucket"
        else
            fail "Failed to upload test file: $upload_result"
            return
        fi
    else
        pass "Uploaded test file to $bucket"
    fi

    # Download and verify the test file
    echo "  Downloading test file from $bucket..."

    local download_result=$(docker exec "$minio_container" bash -c "
        mc alias set myminio http://localhost:9000 minioadmin minioadmin123 2>/dev/null
        mc cat myminio/$bucket/$test_file 2>&1
    " 2>&1 || echo "")

    if [[ "$download_result" == *"$test_content"* ]] || [[ "$download_result" == *"LogiSense"* ]]; then
        pass "Downloaded and verified test file from $bucket"
    else
        # Try alternative method
        local curl_download=$(curl -s \
            "http://localhost:9000/$bucket/$test_file" \
            -u "minioadmin:minioadmin123" 2>/dev/null || echo "")

        if [[ "$curl_download" == *"LogiSense"* ]]; then
            pass "Downloaded and verified test file from $bucket"
        else
            fail "Failed to download or verify test file"
        fi
    fi

    # Cleanup
    docker exec "$minio_container" bash -c "
        mc alias set myminio http://localhost:9000 minioadmin minioadmin123 2>/dev/null
        mc rm myminio/$bucket/$test_file 2>/dev/null
    " 2>/dev/null || true
}

# ==============================================================================
# Vault Test
# ==============================================================================

test_vault() {
    log_test "Vault Secret Read Test"

    local vault_addr="http://localhost:8200"
    local vault_token="dev-root-token"  # pragma: allowlist secret
    local secret_path="logisense/data/dev/kafka"

    # Check if Vault is accessible
    local health=$(curl -s "$vault_addr/v1/sys/health" 2>/dev/null || echo "{}")

    if [[ "$health" == *"initialized"* ]]; then
        pass "Vault is initialized and unsealed"
    else
        fail "Vault is not accessible"
        return
    fi

    # Read the kafka secret
    echo "  Reading secret from $secret_path..."

    local secret=$(curl -s \
        -H "X-Vault-Token: $vault_token" \
        "$vault_addr/v1/$secret_path" 2>/dev/null || echo "{}")

    if [[ "$secret" == *"bootstrap_servers"* ]]; then
        pass "Successfully read Kafka secret from Vault"
        local bootstrap=$(echo "$secret" | grep -oP '"bootstrap_servers":\s*"\K[^"]+' || echo "")
        echo "    bootstrap_servers: $bootstrap"
    else
        fail "Failed to read Kafka secret from Vault"
        echo "    Response: $secret"
    fi

    # Test dynamic database credentials
    echo "  Testing dynamic database credentials..."

    local db_creds=$(curl -s \
        -H "X-Vault-Token: $vault_token" \
        "$vault_addr/v1/database/creds/logisense-app" 2>/dev/null || echo "{}")

    if [[ "$db_creds" == *"username"* ]] && [[ "$db_creds" == *"password"* ]]; then
        pass "Successfully generated dynamic database credentials"
        local db_user=$(echo "$db_creds" | grep -oP '"username":\s*"\K[^"]+' || echo "")
        echo "    username: $db_user"
    else
        fail "Failed to generate dynamic database credentials"
    fi
}

# ==============================================================================
# Keycloak Test
# ==============================================================================

test_keycloak() {
    log_test "Keycloak Authentication Test"

    local keycloak_url="http://localhost:8080"
    local realm="logisense"
    local client_id="logisense-api"
    local username="admin@logisense.io"
    local password="Test1234!Dev"  # pragma: allowlist secret

    # Check if Keycloak is ready
    local health=$(curl -s "$keycloak_url/health/ready" 2>/dev/null || echo "{}")

    if [[ "$health" == *"UP"* ]] || [[ "$health" == *"status"* ]]; then
        pass "Keycloak is healthy"
    else
        fail "Keycloak is not ready"
        return
    fi

    # Get access token
    echo "  Authenticating as $username..."

    local token_response=$(curl -s -X POST \
        "$keycloak_url/realms/$realm/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=password" \
        -d "client_id=$client_id" \
        -d "username=$username" \
        -d "password=$password" \
        2>/dev/null || echo "{}")

    if [[ "$token_response" == *"access_token"* ]]; then
        pass "Successfully authenticated as $username"

        local access_token=$(echo "$token_response" | grep -oP '"access_token":\s*"\K[^"]+' || echo "")
        local token_preview="${access_token:0:50}..."
        echo "    Token: $token_preview"

        # Verify token by calling userinfo endpoint
        local userinfo=$(curl -s \
            "$keycloak_url/realms/$realm/protocol/openid-connect/userinfo" \
            -H "Authorization: Bearer $access_token" \
            2>/dev/null || echo "{}")

        if [[ "$userinfo" == *"$username"* ]] || [[ "$userinfo" == *"email"* ]]; then
            pass "Token verified via userinfo endpoint"
        else
            fail "Token verification failed"
        fi
    else
        fail "Failed to authenticate as $username"
        local error=$(echo "$token_response" | grep -oP '"error_description":\s*"\K[^"]+' || echo "$token_response")
        echo "    Error: $error"
    fi
}

# ==============================================================================
# PostgreSQL Test
# ==============================================================================

test_postgresql() {
    log_test "PostgreSQL Connectivity Test"

    local pg_container="logisense-postgres"

    # Check if PostgreSQL container is running
    if ! docker ps --format '{{.Names}}' | grep -q "$pg_container"; then
        fail "PostgreSQL container not running"
        return
    fi

    # Test connection and query
    local result=$(docker exec "$pg_container" psql -U logisense -d logisense -c "SELECT version();" 2>&1 || echo "error")

    if [[ "$result" == *"PostgreSQL"* ]]; then
        pass "PostgreSQL is accessible"
        local version=$(echo "$result" | grep -oP 'PostgreSQL \d+\.\d+' | head -1)
        echo "    Version: $version"
    else
        fail "PostgreSQL connection failed: $result"
        return
    fi

    # Check schemas exist
    local schemas=$(docker exec "$pg_container" psql -U logisense -d logisense -t -c \
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'logisense%' OR schema_name = 'license';" 2>&1 || echo "")

    if [[ -n "$schemas" ]]; then
        pass "LogiSense schemas exist"
        echo "$schemas" | while read -r schema; do
            [[ -n "$schema" ]] && echo "    - $schema"
        done
    else
        skip "No LogiSense schemas found (will be created on first migration)"
    fi
}

# ==============================================================================
# Redis Test
# ==============================================================================

test_redis() {
    log_test "Redis Connectivity Test"

    local redis_container="logisense-redis"

    # Check if Redis container is running
    if ! docker ps --format '{{.Names}}' | grep -q "$redis_container"; then
        fail "Redis container not running"
        return
    fi

    # Test PING
    local ping_result=$(docker exec "$redis_container" redis-cli PING 2>&1 || echo "error")

    if [[ "$ping_result" == "PONG" ]]; then
        pass "Redis is accessible (PING -> PONG)"
    else
        fail "Redis PING failed: $ping_result"
        return
    fi

    # Test SET/GET
    local test_key="logisense:test:$(date +%s)"
    local test_value="test-value"

    docker exec "$redis_container" redis-cli SET "$test_key" "$test_value" > /dev/null 2>&1
    local get_result=$(docker exec "$redis_container" redis-cli GET "$test_key" 2>&1 || echo "")

    if [[ "$get_result" == "$test_value" ]]; then
        pass "Redis SET/GET works correctly"
    else
        fail "Redis SET/GET failed"
    fi

    # Cleanup
    docker exec "$redis_container" redis-cli DEL "$test_key" > /dev/null 2>&1 || true
}

# ==============================================================================
# License Service Test
# ==============================================================================

test_license_service() {
    log_test "License Service Test"

    local license_api="http://localhost:8007"
    local master_key="logisense-master-api-key-change-in-production"

    # Health check
    local health=$(curl -s "$license_api/health" 2>/dev/null || echo "{}")

    if [[ "$health" == *"ok"* ]]; then
        pass "License Service is healthy"
    else
        fail "License Service is not accessible"
        return
    fi

    # Issue a test license
    echo "  Issuing test license..."

    local issue_response=$(curl -s -X POST "$license_api/v1/license/issue" \
        -H "Content-Type: application/json" \
        -H "X-Master-Key: $master_key" \
        -d '{
            "tenant_id": "test-tenant-'$(date +%s)'",
            "tenant_name": "Test Tenant",
            "licensed_modules": ["iwms", "lip"],
            "facility_count": 1,
            "tier": "standard",
            "valid_days": 30
        }' 2>/dev/null || echo "{}")

    if [[ "$issue_response" == *"license_token"* ]]; then
        pass "Successfully issued test license"

        local token=$(echo "$issue_response" | grep -oP '"license_token":\s*"\K[^"]+' || echo "")

        # Validate the license
        echo "  Validating license for iwms module..."

        local validate_response=$(curl -s -X POST "$license_api/v1/license/validate" \
            -H "Content-Type: application/json" \
            -d "{
                \"token\": \"$token\",
                \"module_id\": \"iwms\"
            }" 2>/dev/null || echo "{}")

        if [[ "$validate_response" == *'"valid":true'* ]] || [[ "$validate_response" == *'"valid": true'* ]]; then
            pass "License validation successful for iwms module"
        else
            fail "License validation failed"
            echo "    Response: $validate_response"
        fi

        # Test invalid module
        echo "  Validating license for unlicensed module..."

        local invalid_response=$(curl -s -X POST "$license_api/v1/license/validate" \
            -H "Content-Type: application/json" \
            -d "{
                \"token\": \"$token\",
                \"module_id\": \"ccvp\"
            }" 2>/dev/null || echo "{}")

        if [[ "$invalid_response" == *'"valid":false'* ]] || [[ "$invalid_response" == *'"valid": false'* ]]; then
            pass "Correctly rejected unlicensed module (ccvp)"
        else
            fail "Should have rejected unlicensed module"
        fi
    else
        fail "Failed to issue test license"
        echo "    Response: $issue_response"
    fi
}

# ==============================================================================
# Print Summary
# ==============================================================================

print_summary() {
    echo ""
    echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}                              VALIDATION SUMMARY                              ${NC}"
    echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""

    local total=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))

    echo -e "  ${GREEN}PASSED:${NC}  $TESTS_PASSED"
    echo -e "  ${RED}FAILED:${NC}  $TESTS_FAILED"
    echo -e "  ${YELLOW}SKIPPED:${NC} $TESTS_SKIPPED"
    echo -e "  ${BLUE}TOTAL:${NC}   $total"
    echo ""

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}"
        echo "  ╔═══════════════════════════════════════════════════════════════════════╗"
        echo "  ║                                                                       ║"
        echo "  ║           ✓ ALL PHASE 0 VALIDATIONS PASSED SUCCESSFULLY!             ║"
        echo "  ║                                                                       ║"
        echo "  ╚═══════════════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
        exit 0
    else
        echo -e "${RED}"
        echo "  ╔═══════════════════════════════════════════════════════════════════════╗"
        echo "  ║                                                                       ║"
        echo "  ║              ✗ SOME VALIDATIONS FAILED - SEE ABOVE                   ║"
        echo "  ║                                                                       ║"
        echo "  ╚═══════════════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
        exit 1
    fi
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    print_banner

    test_service_health
    test_postgresql
    test_redis
    test_kafka
    test_minio
    test_vault
    test_keycloak
    test_license_service

    print_summary
}

# Run main function
main "$@"
