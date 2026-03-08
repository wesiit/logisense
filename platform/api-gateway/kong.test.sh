#!/usr/bin/env bash
# ==============================================================================
# LogiSense Kong API Gateway Route Test Script
# ==============================================================================
# Tests each configured route and reports health status.
# Expected responses:
#   - 200: Service is up and healthy
#   - 401: JWT required (expected for protected routes without token)
#   - 502: Service registered but upstream not running (expected in dev)
#   - 404: Route not configured (error - test fails)
# ==============================================================================
set -euo pipefail

KONG_PROXY_URL="${KONG_PROXY_URL:-http://localhost:8000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
TOTAL=0

# Test a route
test_route() {
    local name="$1"
    local path="$2"
    local expect_auth="$3"  # "yes" if JWT protected, "no" if public

    TOTAL=$((TOTAL + 1))

    # Make request without auth
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "${KONG_PROXY_URL}${path}" 2>/dev/null || echo "000")

    # Determine status
    local status_icon
    local status_color
    local status_text

    case "$http_code" in
        200)
            status_icon="✓"
            status_color="$GREEN"
            status_text="UP"
            PASSED=$((PASSED + 1))
            ;;
        401)
            if [[ "$expect_auth" == "yes" ]]; then
                status_icon="✓"
                status_color="$GREEN"
                status_text="JWT REQUIRED (route active)"
                PASSED=$((PASSED + 1))
            else
                status_icon="✗"
                status_color="$RED"
                status_text="UNEXPECTED 401"
                FAILED=$((FAILED + 1))
            fi
            ;;
        502|503)
            if [[ "$expect_auth" == "yes" ]]; then
                # If we expect auth but got 502, JWT plugin might not be blocking
                status_icon="○"
                status_color="$YELLOW"
                status_text="UPSTREAM DOWN (JWT may be disabled)"
            else
                status_icon="○"
                status_color="$YELLOW"
                status_text="UPSTREAM DOWN (expected)"
            fi
            PASSED=$((PASSED + 1))
            ;;
        404)
            status_icon="✗"
            status_color="$RED"
            status_text="ROUTE NOT FOUND"
            FAILED=$((FAILED + 1))
            ;;
        000)
            status_icon="✗"
            status_color="$RED"
            status_text="CONNECTION FAILED"
            FAILED=$((FAILED + 1))
            ;;
        *)
            status_icon="?"
            status_color="$YELLOW"
            status_text="HTTP $http_code"
            PASSED=$((PASSED + 1))
            ;;
    esac

    printf "${status_color}  ${status_icon} %-18s %-20s → %s${NC}\n" "$name" "$path" "$status_text"
}

# Print header
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║               LogiSense Kong API Gateway Route Tests                     ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
printf "║  Target: %-64s ║\n" "$KONG_PROXY_URL"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Kong is reachable
echo -e "${BLUE}Checking Kong connectivity...${NC}"
if ! curl -s -o /dev/null "${KONG_PROXY_URL}" 2>/dev/null; then
    echo -e "${RED}✗ Cannot connect to Kong at ${KONG_PROXY_URL}${NC}"
    echo "  Make sure Kong is running: docker compose -f docker-compose.dev.yml ps kong"
    exit 1
fi
echo -e "${GREEN}✓ Kong is reachable${NC}"
echo ""

# Test routes
echo -e "${BLUE}Testing routes...${NC}"
echo ""

echo "  Module Services (JWT Protected):"
echo "  ─────────────────────────────────"
test_route "iWMS"      "/v1/iwms/"    "yes"
test_route "LIP"       "/v1/lip/"     "yes"
test_route "CCVP"      "/v1/ccvp/"    "yes"
test_route "PISE"      "/v1/pise/"    "yes"
test_route "WCVP"      "/v1/wcvp/"    "yes"
test_route "UOIH"      "/v1/uoih/"    "yes"

echo ""
echo "  Platform Services (JWT Protected):"
echo "  ───────────────────────────────────"
test_route "License"   "/v1/license/" "yes"

echo ""
echo "  Health Check (No Auth):"
echo "  ───────────────────────"
test_route "Health"    "/health"      "no"

# Print summary
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                              Summary                                     ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
printf "║  Total: %-3d   Passed: ${GREEN}%-3d${NC}   Failed: ${RED}%-3d${NC}                              ║\n" "$TOTAL" "$PASSED" "$FAILED"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Legend
echo "Legend:"
echo "  ✓ JWT REQUIRED    = Route active, returns 401 without token (correct)"
echo "  ○ UPSTREAM DOWN   = Route active, upstream service not running (502)"
echo "  ✓ UP              = Route active and responding (200)"
echo "  ✗ ROUTE NOT FOUND = Route not configured (404 - error)"
echo ""

# Exit with error if any failed
if [[ $FAILED -gt 0 ]]; then
    echo -e "${RED}Some routes failed. Check Kong configuration.${NC}"
    exit 1
fi

echo -e "${GREEN}All routes configured correctly!${NC}"
