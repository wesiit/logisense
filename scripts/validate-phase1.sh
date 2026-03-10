#!/usr/bin/env bash
# =============================================================================
# LogiSense Phase 1 Integration Test
# =============================================================================
# Tests the complete Phase 1 stack working together:
# - Keycloak authentication
# - iWMS API (inventory, orders, waves, tasks)
# - Airflow ETL pipeline
# - UOIH API (KPIs, alerts)
#
# PREREQUISITES:
# 1. Docker containers running:
#    docker compose -f docker-compose.dev.yml up -d
#
# 2. Database migrations applied:
#    cd modules/iwms && alembic upgrade head
#    cd modules/uoih && alembic upgrade head
#
# 3. Keycloak configured with test user:
#    - User: manager@logisense.io
#    - Password: manager123
#    - Realm: logisense
#    - Client: logisense-api
#
# 4. OR set SKIP_AUTH=true to bypass authentication (for dev only)
#
# USAGE:
#   ./scripts/validate-phase1.sh                    # Full test with auth
#   SKIP_AUTH=true ./scripts/validate-phase1.sh    # Skip auth (dev mode)
#   PIPELINE_WAIT_SECONDS=60 ./scripts/validate-phase1.sh  # Wait longer
# =============================================================================

set -euo pipefail

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
IWMS_API_URL="${IWMS_API_URL:-http://localhost:8011}"
UOIH_API_URL="${UOIH_API_URL:-http://localhost:8006}"
FACILITY_ID="${FACILITY_ID:-TEST-FACILITY-001}"
TEST_USER="${TEST_USER:-manager@logisense.io}"
TEST_PASSWORD="${TEST_PASSWORD:-Test1234!Dev}"
KEYCLOAK_REALM="${KEYCLOAK_REALM:-logisense}"
KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-logisense-api}"
KEYCLOAK_CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET:-logisense-api-secret-dev}"
PIPELINE_WAIT_SECONDS="${PIPELINE_WAIT_SECONDS:-30}"
SKIP_AUTH="${SKIP_AUTH:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
FAIL_COUNT=0

# Cleanup tracking
CLEANUP_IDS=()

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((++PASS_COUNT)) || true
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((++FAIL_COUNT)) || true
}

check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is required but not installed."
        exit 1
    fi
}

# JSON parser using Python (jq replacement)
json_get() {
    local json="$1"
    local path="$2"
    local default="${3:-}"

    python3 -c "
import json
import sys

try:
    data = json.loads('''$json''')
    keys = '$path'.split('.')
    result = data
    for key in keys:
        if key.startswith('[') and key.endswith(']'):
            idx = int(key[1:-1])
            result = result[idx] if isinstance(result, list) and len(result) > idx else None
        elif key:
            result = result.get(key) if isinstance(result, dict) else None
        if result is None:
            break
    if result is None:
        print('$default')
    else:
        print(result)
except Exception as e:
    print('$default')
" 2>/dev/null
}

# JSON array length using Python
json_length() {
    local json="$1"
    local path="$2"

    python3 -c "
import json

try:
    data = json.loads('''$json''')
    keys = '$path'.split('.') if '$path' else []
    result = data
    for key in keys:
        if key.startswith('[') and key.endswith(']'):
            idx = int(key[1:-1])
            result = result[idx] if isinstance(result, list) and len(result) > idx else []
        elif key:
            result = result.get(key, []) if isinstance(result, dict) else []
    print(len(result) if isinstance(result, list) else 0)
except:
    print(0)
" 2>/dev/null
}

# JSON filter for pipeline alerts
json_filter_pipeline_alerts() {
    local json="$1"

    python3 -c "
import json

try:
    data = json.loads('''$json''')
    alerts = data.get('alerts', [])
    pipeline_alerts = [a for a in alerts if 'PIPELINE' in a.get('alert_type', '') or 'ETL' in a.get('alert_type', '')]
    print(len(pipeline_alerts))
except:
    print(0)
" 2>/dev/null
}

# HTTP request helper with error handling
http_request() {
    local method="$1"
    local url="$2"
    local data="${3:-}"
    local expected_code="${4:-200}"

    local response
    local http_code
    local auth_header=""

    # Only add auth header if token is set
    if [ -n "$ACCESS_TOKEN" ]; then
        auth_header="-H \"Authorization: Bearer $ACCESS_TOKEN\""
    fi

    if [ -n "$data" ]; then
        if [ -n "$ACCESS_TOKEN" ]; then
            response=$(curl -s -w "\n%{http_code}" -X "$method" \
                -H "Authorization: Bearer $ACCESS_TOKEN" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$url" 2>/dev/null)
        else
            response=$(curl -s -w "\n%{http_code}" -X "$method" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$url" 2>/dev/null)
        fi
    else
        if [ -n "$ACCESS_TOKEN" ]; then
            response=$(curl -s -w "\n%{http_code}" -X "$method" \
                -H "Authorization: Bearer $ACCESS_TOKEN" \
                -H "Content-Type: application/json" \
                "$url" 2>/dev/null)
        else
            response=$(curl -s -w "\n%{http_code}" -X "$method" \
                -H "Content-Type: application/json" \
                "$url" 2>/dev/null)
        fi
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq "$expected_code" ]; then
        echo "$body"
        return 0
    else
        echo "HTTP $http_code: $body" >&2
        return 1
    fi
}

# =============================================================================
# Check Dependencies
# =============================================================================

check_dependency curl
check_dependency python3

# =============================================================================
# Step 1: Get Keycloak Token
# =============================================================================

log_info "Step 1: Authenticating..."

if [ "$SKIP_AUTH" = "true" ]; then
    log_info "SKIP_AUTH=true, using empty auth header"
    ACCESS_TOKEN=""
    log_pass "Step 1: Authentication skipped (SKIP_AUTH=true)"
else
    # Build token request
    TOKEN_ENDPOINT="$KEYCLOAK_URL/realms/$KEYCLOAK_REALM/protocol/openid-connect/token"

    # Check if Keycloak is reachable
    if curl -s --connect-timeout 3 "$KEYCLOAK_URL" > /dev/null 2>&1; then
        if [ -n "$KEYCLOAK_CLIENT_SECRET" ]; then
            # Confidential client
            TOKEN_RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
                -H "Content-Type: application/x-www-form-urlencoded" \
                -d "grant_type=password" \
                -d "client_id=$KEYCLOAK_CLIENT_ID" \
                -d "client_secret=$KEYCLOAK_CLIENT_SECRET" \
                -d "username=$TEST_USER" \
                -d "password=$TEST_PASSWORD" 2>/dev/null)
        else
            # Public client
            TOKEN_RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
                -H "Content-Type: application/x-www-form-urlencoded" \
                -d "grant_type=password" \
                -d "client_id=$KEYCLOAK_CLIENT_ID" \
                -d "username=$TEST_USER" \
                -d "password=$TEST_PASSWORD" 2>/dev/null)
        fi

        ACCESS_TOKEN=$(json_get "$TOKEN_RESPONSE" "access_token" "")

        if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
            log_pass "Step 1: Got Keycloak token for $TEST_USER"
        else
            ERROR_MSG=$(json_get "$TOKEN_RESPONSE" "error_description" "Unknown error")
            log_fail "Step 1: Failed to get Keycloak token - $ERROR_MSG"
            echo ""
            echo "  To run without authentication, use: SKIP_AUTH=true $0"
            echo "  Or start Keycloak: docker compose -f docker-compose.dev.yml up -d keycloak"
            echo ""
            exit 1
        fi
    else
        log_fail "Step 1: Keycloak not available at $KEYCLOAK_URL"
        echo ""
        echo "  To run without authentication, use: SKIP_AUTH=true $0"
        echo "  Or start Keycloak: docker compose -f docker-compose.dev.yml up -d keycloak"
        echo ""
        exit 1
    fi
fi

# =============================================================================
# Step 2: Create Test SKU and Location (if needed)
# =============================================================================

log_info "Step 2: Setting up test SKU and location..."

# Generate unique test identifiers
TEST_RUN_ID=$(date +%s)
TEST_SKU_CODE="TEST-SKU-$TEST_RUN_ID"
TEST_LOCATION_CODE="TEST-LOC-$TEST_RUN_ID"
TEST_ORDER_NUMBER="TEST-ORD-$TEST_RUN_ID"

# Create test SKU
SKU_PAYLOAD=$(cat <<EOF
{
    "sku_code": "$TEST_SKU_CODE",
    "sku_name": "Integration Test SKU $TEST_RUN_ID",
    "category_l1": "TEST",
    "category_l2": "INTEGRATION",
    "unit_of_measure": "EA",
    "weight_kg": 1.0,
    "is_perishable": false,
    "is_active": true
}
EOF
)

SKU_RESPONSE=$(http_request POST "$IWMS_API_URL/v1/iwms/inventory/skus" "$SKU_PAYLOAD" 201) || {
    log_fail "Step 2a: Failed to create test SKU"
    exit 1
}

SKU_ID=$(json_get "$SKU_RESPONSE" "id" "")
if [ -n "$SKU_ID" ] && [ "$SKU_ID" != "null" ]; then
    log_pass "Step 2a: Created test SKU $TEST_SKU_CODE (ID: $SKU_ID)"
    CLEANUP_IDS+=("sku:$SKU_ID")
else
    log_fail "Step 2a: Failed to create test SKU - no ID returned"
    exit 1
fi

# Create test location
LOCATION_PAYLOAD=$(cat <<EOF
{
    "facility_id": "$FACILITY_ID",
    "zone_id": "TEST-ZONE",
    "aisle": "T1",
    "bay": "01",
    "level": "A",
    "bin": "001",
    "location_code": "$TEST_LOCATION_CODE",
    "location_type": "PICK",
    "is_active": true
}
EOF
)

LOCATION_RESPONSE=$(http_request POST "$IWMS_API_URL/v1/iwms/inventory/locations" "$LOCATION_PAYLOAD" 201) || {
    log_fail "Step 2b: Failed to create test location"
    exit 1
}

LOCATION_ID=$(json_get "$LOCATION_RESPONSE" "id" "")
if [ -n "$LOCATION_ID" ] && [ "$LOCATION_ID" != "null" ]; then
    log_pass "Step 2b: Created test location $TEST_LOCATION_CODE (ID: $LOCATION_ID)"
    CLEANUP_IDS+=("location:$LOCATION_ID")
else
    log_fail "Step 2b: Failed to create test location - no ID returned"
    exit 1
fi

# =============================================================================
# Step 3: Receive 10 units via inventory movement
# =============================================================================

log_info "Step 3: Receiving 10 units of test SKU..."

MOVEMENT_PAYLOAD=$(cat <<EOF
{
    "facility_id": "$FACILITY_ID",
    "movement_type": "RECEIVE",
    "sku_id": "$SKU_ID",
    "quantity": 10,
    "to_location_id": "$LOCATION_ID",
    "reference_id": "TEST-RECEIPT-$TEST_RUN_ID",
    "reference_type": "INTEGRATION_TEST",
    "notes": "Phase 1 integration test receipt"
}
EOF
)

MOVEMENT_RESPONSE=$(http_request POST "$IWMS_API_URL/v1/iwms/inventory/movements" "$MOVEMENT_PAYLOAD" 201) || {
    log_fail "Step 3: Failed to create inventory movement"
    exit 1
}

MOVEMENT_ID=$(json_get "$MOVEMENT_RESPONSE" "id" "")
if [ -n "$MOVEMENT_ID" ] && [ "$MOVEMENT_ID" != "null" ]; then
    log_pass "Step 3: Received 10 units (Movement ID: $MOVEMENT_ID)"
else
    log_fail "Step 3: Failed to create inventory movement - no ID returned"
    exit 1
fi

# =============================================================================
# Step 4: Verify inventory position shows 10 units
# =============================================================================

log_info "Step 4: Verifying inventory position..."

# Small delay to ensure position is updated
sleep 1

POSITIONS_RESPONSE=$(http_request GET "$IWMS_API_URL/v1/iwms/inventory/positions?facility_id=$FACILITY_ID&sku_id=$SKU_ID" "" 200) || {
    log_fail "Step 4: Failed to fetch inventory positions"
    exit 1
}

POSITION_QTY=$(json_get "$POSITIONS_RESPONSE" "items.[0].quantity" "0")
if [ "$POSITION_QTY" -eq 10 ]; then
    log_pass "Step 4: Inventory position shows 10 units"
else
    log_fail "Step 4: Expected 10 units, got $POSITION_QTY"
fi

# =============================================================================
# Step 5: Create an order with 3 units
# =============================================================================

log_info "Step 5: Creating order for 3 units..."

ORDER_PAYLOAD=$(cat <<EOF
{
    "facility_id": "$FACILITY_ID",
    "order_number": "$TEST_ORDER_NUMBER",
    "order_type": "OUTBOUND",
    "priority": 5,
    "customer_id": "TEST-CUSTOMER",
    "lines": [
        {
            "sku_id": "$SKU_ID",
            "quantity_ordered": 3
        }
    ]
}
EOF
)

ORDER_RESPONSE=$(http_request POST "$IWMS_API_URL/v1/iwms/orders" "$ORDER_PAYLOAD" 201) || {
    log_fail "Step 5: Failed to create order"
    exit 1
}

ORDER_ID=$(json_get "$ORDER_RESPONSE" "id" "")
if [ -n "$ORDER_ID" ] && [ "$ORDER_ID" != "null" ]; then
    log_pass "Step 5: Created order $TEST_ORDER_NUMBER (ID: $ORDER_ID)"
    CLEANUP_IDS+=("order:$ORDER_ID")
else
    log_fail "Step 5: Failed to create order - no ID returned"
    exit 1
fi

# =============================================================================
# Step 6: Create a wave from the order
# =============================================================================

log_info "Step 6: Creating wave from order..."

WAVE_PAYLOAD=$(cat <<EOF
{
    "facility_id": "$FACILITY_ID",
    "order_ids": ["$ORDER_ID"]
}
EOF
)

WAVE_RESPONSE=$(http_request POST "$IWMS_API_URL/v1/iwms/waves" "$WAVE_PAYLOAD" 201) || {
    log_fail "Step 6: Failed to create wave"
    exit 1
}

WAVE_ID=$(json_get "$WAVE_RESPONSE" "id" "")
WAVE_NUMBER=$(json_get "$WAVE_RESPONSE" "wave_number" "")
if [ -n "$WAVE_ID" ] && [ "$WAVE_ID" != "null" ]; then
    log_pass "Step 6: Created wave $WAVE_NUMBER (ID: $WAVE_ID)"
    CLEANUP_IDS+=("wave:$WAVE_ID")
else
    log_fail "Step 6: Failed to create wave - no ID returned"
    exit 1
fi

# =============================================================================
# Step 7: Release the wave
# =============================================================================

log_info "Step 7: Releasing wave..."

RELEASE_RESPONSE=$(http_request POST "$IWMS_API_URL/v1/iwms/waves/$WAVE_ID/release" "" 200) || {
    log_fail "Step 7: Failed to release wave"
    exit 1
}

WAVE_STATUS=$(json_get "$RELEASE_RESPONSE" "status" "")
TASK_COUNT=$(json_length "$RELEASE_RESPONSE" "tasks")

if [ "$WAVE_STATUS" = "RELEASED" ]; then
    log_pass "Step 7a: Wave status is RELEASED"
else
    log_fail "Step 7a: Expected wave status RELEASED, got $WAVE_STATUS"
fi

if [ "$TASK_COUNT" -gt 0 ]; then
    log_pass "Step 7b: $TASK_COUNT task(s) created"
else
    log_fail "Step 7b: No tasks were created"
fi

# Get the first task ID
TASK_ID=$(json_get "$RELEASE_RESPONSE" "tasks.[0].id" "")
if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "null" ]; then
    # Try fetching tasks separately
    TASKS_RESPONSE=$(http_request GET "$IWMS_API_URL/v1/iwms/tasks?facility_id=$FACILITY_ID&wave_id=$WAVE_ID" "" 200)
    TASK_ID=$(json_get "$TASKS_RESPONSE" "items.[0].id" "")
fi

if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "null" ]; then
    log_fail "Step 7c: Could not find task ID"
    exit 1
fi

log_info "Found pick task ID: $TASK_ID"

# =============================================================================
# Step 8: Complete the pick task
# =============================================================================

log_info "Step 8: Completing pick task..."

COMPLETE_PAYLOAD=$(cat <<EOF
{
    "quantity_completed": 3,
    "notes": "Completed by integration test"
}
EOF
)

COMPLETE_RESPONSE=$(http_request PATCH "$IWMS_API_URL/v1/iwms/tasks/$TASK_ID/complete" "$COMPLETE_PAYLOAD" 200) || {
    log_fail "Step 8: Failed to complete task"
    exit 1
}

TASK_STATUS=$(json_get "$COMPLETE_RESPONSE" "status" "")
if [ "$TASK_STATUS" = "COMPLETE" ]; then
    log_pass "Step 8: Pick task completed successfully"
else
    log_fail "Step 8: Expected task status COMPLETE, got $TASK_STATUS"
fi

# =============================================================================
# Step 9: Wait for Airflow pipeline
# =============================================================================

log_info "Step 9: Waiting $PIPELINE_WAIT_SECONDS seconds for Airflow pipeline..."

# Show a simple progress indicator
for ((i=1; i<=PIPELINE_WAIT_SECONDS; i++)); do
    printf "\r  Processing... %d/%d seconds" "$i" "$PIPELINE_WAIT_SECONDS"
    sleep 1
done
printf "\n"

log_pass "Step 9: Waited for pipeline processing"

# =============================================================================
# Step 10: Verify daily KPIs show picks_completed > 0
# =============================================================================

log_info "Step 10: Checking daily KPIs..."

TODAY=$(date +%Y-%m-%d)

KPIS_RESPONSE=$(http_request GET "$UOIH_API_URL/v1/uoih/kpis/daily?facility_id=$FACILITY_ID&date_from=$TODAY&date_to=$TODAY" "" 200) || {
    # KPIs might not be available if Iceberg catalog is not running
    log_fail "Step 10: Failed to fetch daily KPIs (UOIH API may not be running or Iceberg not configured)"
    KPIS_RESPONSE=""
}

if [ -n "$KPIS_RESPONSE" ]; then
    PICKS_COMPLETED=$(json_get "$KPIS_RESPONSE" "kpis.[0].picks_completed" "0")

    if [ "$PICKS_COMPLETED" -gt 0 ]; then
        log_pass "Step 10: Daily KPIs show picks_completed = $PICKS_COMPLETED"
    else
        log_fail "Step 10: Expected picks_completed > 0, got $PICKS_COMPLETED"
        log_info "  (This may indicate Airflow ETL hasn't processed events yet)"
    fi
fi

# =============================================================================
# Step 11: Verify no pipeline failure alerts
# =============================================================================

log_info "Step 11: Checking for pipeline failure alerts..."

ALERTS_RESPONSE=$(http_request GET "$UOIH_API_URL/v1/uoih/alerts/active?facility_id=$FACILITY_ID" "" 200) || {
    log_fail "Step 11: Failed to fetch active alerts (UOIH API may not be running)"
    ALERTS_RESPONSE=""
}

if [ -n "$ALERTS_RESPONSE" ]; then
    # Check for pipeline-related alerts
    PIPELINE_ALERTS=$(json_filter_pipeline_alerts "$ALERTS_RESPONSE")
    TOTAL_ALERTS=$(json_get "$ALERTS_RESPONSE" "total" "0")

    if [ "$PIPELINE_ALERTS" -eq 0 ]; then
        log_pass "Step 11: No pipeline failure alerts found (total alerts: $TOTAL_ALERTS)"
    else
        log_fail "Step 11: Found $PIPELINE_ALERTS pipeline-related alert(s)"
    fi
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "============================================================================="
echo "                     PHASE 1 INTEGRATION TEST RESULTS"
echo "============================================================================="
echo ""
printf "  ${GREEN}PASSED:${NC} %d\n" "$PASS_COUNT"
printf "  ${RED}FAILED:${NC} %d\n" "$FAIL_COUNT"
echo ""

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "  ${GREEN}All tests passed!${NC}"
else
    echo -e "  ${YELLOW}Some tests failed. Check output above for details.${NC}"
fi

echo ""
echo "============================================================================="
echo ""
echo "Phase 1 integration test complete. PASS: $PASS_COUNT, FAIL: $FAIL_COUNT"
echo ""

# Exit with appropriate code
if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

exit 0
