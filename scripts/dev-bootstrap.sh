#!/usr/bin/env bash
# ==============================================================================
# LogiSense Development Environment Bootstrap
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                    LogiSense Development Environment                     ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check for .env file
if [[ ! -f ".env" ]]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
fi

# Start all services
echo "🚀 Starting services..."
docker compose -f docker-compose.dev.yml up -d --wait

echo ""
echo "✅ All services are running!"
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                           Service URLs                                   ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
echo "║  PostgreSQL     │ localhost:5432    │ db=logisense user=logisense       ║"
echo "║  Redis          │ localhost:6379    │ redis-cli                         ║"
echo "║  MinIO Console  │ http://localhost:9001  │ minioadmin / minioadmin123   ║"
echo "║  MinIO API      │ http://localhost:9000  │ S3-compatible endpoint       ║"
echo "║  Kafka          │ localhost:9092    │ Bootstrap server                  ║"
echo "║  Keycloak       │ http://localhost:8080  │ admin / admin                ║"
echo "║  Kong Proxy     │ http://localhost:8000  │ API Gateway                  ║"
echo "║  Kong Admin     │ http://localhost:8001  │ Admin API                    ║"
echo "║  Vault          │ http://localhost:8200  │ Token: dev-root-token        ║"
echo "║  MailHog        │ http://localhost:8025  │ Email UI (SMTP: 1025)        ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📖 View logs:     docker compose -f docker-compose.dev.yml logs -f [service]"
echo "🛑 Stop services: ./scripts/dev-teardown.sh"
echo ""
