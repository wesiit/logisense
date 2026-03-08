#!/usr/bin/env bash
# ==============================================================================
# LogiSense Developer Bootstrap Script
# ==============================================================================
# Comprehensive setup script for local development environment
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

# Configuration
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.dev.yml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
VAULT_INIT_SCRIPT="$PROJECT_ROOT/platform/secret-management/vault-init.sh"
TIMEOUT_SECONDS=300

# ==============================================================================
# Utility Functions
# ==============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                          ║"
    echo "║     ██╗      ██████╗  ██████╗ ██╗███████╗███████╗███╗   ██╗███████╗     ║"
    echo "║     ██║     ██╔═══██╗██╔════╝ ██║██╔════╝██╔════╝████╗  ██║██╔════╝     ║"
    echo "║     ██║     ██║   ██║██║  ███╗██║███████╗█████╗  ██╔██╗ ██║███████╗     ║"
    echo "║     ██║     ██║   ██║██║   ██║██║╚════██║██╔══╝  ██║╚██╗██║╚════██║     ║"
    echo "║     ███████╗╚██████╔╝╚██████╔╝██║███████║███████╗██║ ╚████║███████║     ║"
    echo "║     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝     ║"
    echo "║                                                                          ║"
    echo "║                    Developer Environment Bootstrap                       ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_step() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}"
}

# ==============================================================================
# Prerequisite Checks
# ==============================================================================

check_prerequisites() {
    log_step "Checking Prerequisites"

    local all_ok=true

    # Docker
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version | grep -oP '\d+\.\d+' | head -1)
        log_success "Docker $docker_version"
    else
        log_error "Docker not installed"
        echo "       Install: https://docs.docker.com/get-docker/"
        all_ok=false
    fi

    # Docker Compose
    if docker compose version &> /dev/null; then
        local compose_version=$(docker compose version --short 2>/dev/null || echo "v2+")
        log_success "Docker Compose $compose_version"
    else
        log_error "Docker Compose not installed"
        echo "       Install: https://docs.docker.com/compose/install/"
        all_ok=false
    fi

    # kubectl (optional)
    if command -v kubectl &> /dev/null; then
        local kubectl_version=$(kubectl version --client -o json 2>/dev/null | grep -oP '"gitVersion":\s*"\K[^"]+' || echo "installed")
        log_success "kubectl $kubectl_version"
    else
        log_warning "kubectl not installed (optional for local dev)"
        echo "       Install: https://kubernetes.io/docs/tasks/tools/"
    fi

    # Helm (optional)
    if command -v helm &> /dev/null; then
        local helm_version=$(helm version --short 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' || echo "installed")
        log_success "Helm $helm_version"
    else
        log_warning "Helm not installed (optional for local dev)"
        echo "       Install: https://helm.sh/docs/intro/install/"
    fi

    # Python 3.12+
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | grep -oP '\d+\.\d+')
        local python_major=$(echo "$python_version" | cut -d. -f1)
        local python_minor=$(echo "$python_version" | cut -d. -f2)
        if [[ "$python_major" -ge 3 && "$python_minor" -ge 12 ]]; then
            log_success "Python $python_version"
        else
            log_error "Python 3.12+ required (found $python_version)"
            echo "       Install: https://www.python.org/downloads/"
            all_ok=false
        fi
    else
        log_error "Python not installed"
        echo "       Install: https://www.python.org/downloads/"
        all_ok=false
    fi

    # Node.js 18+
    if command -v node &> /dev/null; then
        local node_version=$(node --version | grep -oP '\d+' | head -1)
        if [[ "$node_version" -ge 18 ]]; then
            log_success "Node.js v$node_version"
        else
            log_error "Node.js 18+ required (found v$node_version)"
            echo "       Install: https://nodejs.org/"
            all_ok=false
        fi
    else
        log_warning "Node.js not installed (required for frontend development)"
        echo "       Install: https://nodejs.org/"
    fi

    # curl
    if command -v curl &> /dev/null; then
        log_success "curl installed"
    else
        log_error "curl not installed"
        echo "       Install: apt-get install curl"
        all_ok=false
    fi

    # jq
    if command -v jq &> /dev/null; then
        log_success "jq installed"
    else
        log_warning "jq not installed (recommended)"
        echo "       Install: apt-get install jq"
    fi

    if [[ "$all_ok" == false ]]; then
        echo ""
        log_error "Some required prerequisites are missing. Please install them and try again."
        exit 1
    fi

    echo ""
    log_success "All required prerequisites are installed!"
}

# ==============================================================================
# Environment Setup
# ==============================================================================

setup_env_file() {
    log_step "Setting Up Environment"

    if [[ -f "$ENV_FILE" ]]; then
        log_success ".env file already exists"
    elif [[ -f "$ENV_EXAMPLE" ]]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log_success "Created .env from .env.example"
    else
        # Create default .env file
        cat > "$ENV_FILE" << 'EOF'
# ==============================================================================
# LogiSense Development Environment Configuration
# ==============================================================================

# PostgreSQL
POSTGRES_DB=logisense
POSTGRES_USER=logisense
POSTGRES_PASSWORD=logisense_dev

# Keycloak
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123

# Vault
VAULT_DEV_ROOT_TOKEN_ID=dev-root-token

# License Service
LICENSE_JWT_SECRET=logisense-license-jwt-secret-change-in-production
LICENSE_MASTER_API_KEY=logisense-master-api-key-change-in-production

# Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# Dev License Token (populated by bootstrap script)
LOGISENSE_DEV_LICENSE_TOKEN=
EOF
        log_success "Created default .env file"
    fi
}

# ==============================================================================
# Docker Compose Services
# ==============================================================================

start_services() {
    log_step "Starting Docker Compose Services"

    cd "$PROJECT_ROOT"

    log_info "Pulling latest images..."
    docker compose -f "$COMPOSE_FILE" pull --quiet 2>/dev/null || true

    log_info "Starting services..."
    docker compose -f "$COMPOSE_FILE" up -d

    echo ""
    log_success "Docker Compose services started"
}

wait_for_services() {
    log_step "Waiting for Services to be Healthy"

    local services=(
        "postgres:5432:PostgreSQL"
        "redis:6379:Redis"
        "kafka:9092:Kafka"
        "minio:9000:MinIO"
        "keycloak:8080:Keycloak"
        "kong:8001:Kong"
        "vault:8200:Vault"
    )

    local start_time=$(date +%s)

    for service_info in "${services[@]}"; do
        IFS=':' read -r service port name <<< "$service_info"

        printf "  Waiting for %-12s " "$name..."

        while true; do
            if docker compose -f "$COMPOSE_FILE" ps "$service" 2>/dev/null | grep -q "healthy"; then
                echo -e "${GREEN}✓ healthy${NC}"
                break
            fi

            # Check if port is responding as fallback
            if nc -z localhost "$port" 2>/dev/null; then
                if docker compose -f "$COMPOSE_FILE" ps "$service" 2>/dev/null | grep -q "Up"; then
                    echo -e "${GREEN}✓ running${NC}"
                    break
                fi
            fi

            local elapsed=$(($(date +%s) - start_time))
            if [[ $elapsed -ge $TIMEOUT_SECONDS ]]; then
                echo -e "${RED}✗ timeout${NC}"
                log_error "Service $name did not become healthy within timeout"
                exit 1
            fi

            sleep 2
        done
    done

    echo ""
    log_success "All services are healthy!"
}

# ==============================================================================
# Vault Initialization
# ==============================================================================

init_vault() {
    log_step "Initializing Vault Secrets"

    if [[ -f "$VAULT_INIT_SCRIPT" ]]; then
        export VAULT_ADDR="http://localhost:8200"
        export VAULT_TOKEN="dev-root-token"

        bash "$VAULT_INIT_SCRIPT" 2>&1 | sed 's/^/  /'

        log_success "Vault initialized with dev secrets"
    else
        log_warning "Vault init script not found, skipping"
    fi
}

# ==============================================================================
# License Token Generation
# ==============================================================================

generate_dev_license() {
    log_step "Generating Development License Token"

    local license_api="http://localhost:8007"
    local master_key="logisense-master-api-key-change-in-production"

    # Wait for license-api to be ready
    local max_wait=60
    local waited=0

    printf "  Waiting for License API..."
    while ! curl -s "$license_api/health" > /dev/null 2>&1; do
        sleep 2
        waited=$((waited + 2))
        if [[ $waited -ge $max_wait ]]; then
            echo -e "${YELLOW} skipped (not running)${NC}"
            log_warning "License API not available, skipping license generation"
            return 0
        fi
    done
    echo -e "${GREEN} ready${NC}"

    # Issue license for all modules
    local response=$(curl -s -X POST "$license_api/v1/license/issue" \
        -H "Content-Type: application/json" \
        -H "X-Master-Key: $master_key" \
        -d '{
            "tenant_id": "dev-tenant",
            "tenant_name": "LogiSense Development",
            "licensed_modules": ["iwms", "lip", "ccvp", "pise", "wcvp", "uoih"],
            "facility_count": 10,
            "tier": "enterprise",
            "valid_days": 365
        }')

    local token=$(echo "$response" | grep -oP '"license_token":\s*"\K[^"]+' || echo "")

    if [[ -n "$token" ]]; then
        # Update .env file with token
        if grep -q "LOGISENSE_DEV_LICENSE_TOKEN=" "$ENV_FILE"; then
            sed -i "s|LOGISENSE_DEV_LICENSE_TOKEN=.*|LOGISENSE_DEV_LICENSE_TOKEN=$token|" "$ENV_FILE"
        else
            echo "LOGISENSE_DEV_LICENSE_TOKEN=$token" >> "$ENV_FILE"
        fi
        log_success "Dev license token generated and saved to .env"
        echo "  Modules: iwms, lip, ccvp, pise, wcvp, uoih"
        echo "  Tier: enterprise"
        echo "  Valid: 365 days"
    else
        log_warning "Failed to generate license token"
        echo "  Response: $response"
    fi
}

# ==============================================================================
# Connectivity Check
# ==============================================================================

check_connectivity() {
    log_step "Running Connectivity Checks"

    local endpoints=(
        "Kong Gateway|http://localhost:8000/"
        "Kong Admin|http://localhost:8001/status"
        "Keycloak|http://localhost:8080/health/ready"
        "Vault|http://localhost:8200/v1/sys/health"
        "MinIO Console|http://localhost:9001/"
        "Prometheus|http://localhost:9090/-/healthy"
        "Grafana|http://localhost:3000/api/health"
        "License API|http://localhost:8007/health"
    )

    local all_ok=true

    for endpoint_info in "${endpoints[@]}"; do
        IFS='|' read -r name url <<< "$endpoint_info"

        printf "  %-16s " "$name"

        local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5 2>/dev/null || echo "000")

        if [[ "$status" =~ ^(200|204|429|472|473)$ ]]; then
            echo -e "${GREEN}✓ OK${NC} (HTTP $status)"
        elif [[ "$status" == "000" ]]; then
            echo -e "${RED}✗ Not reachable${NC}"
            all_ok=false
        else
            echo -e "${YELLOW}? HTTP $status${NC}"
        fi
    done

    echo ""
    if [[ "$all_ok" == true ]]; then
        log_success "All connectivity checks passed!"
    else
        log_warning "Some services are not reachable"
    fi
}

# ==============================================================================
# Success Banner
# ==============================================================================

print_success_banner() {
    echo ""
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                          ║"
    echo "║                    ✓ Development Environment Ready!                      ║"
    echo "║                                                                          ║"
    echo "╠══════════════════════════════════════════════════════════════════════════╣"
    echo "║                                                                          ║"
    echo "║  Service URLs:                                                           ║"
    echo "║  ─────────────────────────────────────────────────────────────────────   ║"
    echo "║  Kong Gateway      │ http://localhost:8000                               ║"
    echo "║  Kong Admin API    │ http://localhost:8001                               ║"
    echo "║  Keycloak          │ http://localhost:8080   (admin/admin)               ║"
    echo "║  Vault             │ http://localhost:8200   (token: dev-root-token)     ║"
    echo "║  MinIO Console     │ http://localhost:9001   (minioadmin/minioadmin123)  ║"
    echo "║  PostgreSQL        │ localhost:5432          (logisense/logisense_dev)   ║"
    echo "║  Redis             │ localhost:6379                                      ║"
    echo "║  Kafka             │ localhost:9092                                      ║"
    echo "║  Prometheus        │ http://localhost:9090                               ║"
    echo "║  Grafana           │ http://localhost:3000   (admin/admin)               ║"
    echo "║  Loki              │ http://localhost:3100                               ║"
    echo "║  License API       │ http://localhost:8007                               ║"
    echo "║  MailHog           │ http://localhost:8025                               ║"
    echo "║                                                                          ║"
    echo "╠══════════════════════════════════════════════════════════════════════════╣"
    echo "║                                                                          ║"
    echo "║  Next Steps:                                                             ║"
    echo "║  1. Run ./scripts/validate-phase0.sh to verify all integrations          ║"
    echo "║  2. Start developing your module in modules/<module-name>/               ║"
    echo "║  3. Check Grafana dashboards at http://localhost:3000                    ║"
    echo "║                                                                          ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    print_banner

    check_prerequisites
    setup_env_file
    start_services
    wait_for_services
    init_vault
    generate_dev_license
    check_connectivity
    print_success_banner
}

# Run main function
main "$@"
