#!/usr/bin/env bash
# ==============================================================================
# LogiSense Development Environment Teardown
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🛑 Stopping LogiSense development services..."
docker compose -f docker-compose.dev.yml down -v

echo ""
echo "✅ All services stopped and volumes removed."
echo ""
echo "💡 To restart: ./scripts/dev-bootstrap.sh"
echo ""
