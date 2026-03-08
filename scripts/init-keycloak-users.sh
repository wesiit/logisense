#!/usr/bin/env bash
# ==============================================================================
# LogiSense Keycloak Test Users Initialization
# ==============================================================================
set -euo pipefail

KEYCLOAK_CONTAINER="${KEYCLOAK_CONTAINER:-logisense-keycloak}"
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
REALM="logisense"
DEFAULT_PASSWORD="${DEFAULT_PASSWORD:-Test1234!Dev}"

echo "Initializing Keycloak test users..."

# Wait for Keycloak to be healthy
echo "Waiting for Keycloak to be healthy..."
until docker inspect --format='{{.State.Health.Status}}' "$KEYCLOAK_CONTAINER" 2>/dev/null | grep -q "healthy"; do
    sleep 2
done
echo "Keycloak is ready."

# Run user setup inside container
docker exec "$KEYCLOAK_CONTAINER" sh -c "
/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user $KEYCLOAK_ADMIN --password $KEYCLOAK_ADMIN_PASSWORD

# Delete existing test users
for user in admin manager operator analyst; do
  USER_ID=\$(/opt/keycloak/bin/kcadm.sh get users -r $REALM -q username=\$user --fields id 2>/dev/null | grep id | cut -d'\"' -f4 || echo '')
  if [ -n \"\$USER_ID\" ]; then
    /opt/keycloak/bin/kcadm.sh delete users/\$USER_ID -r $REALM 2>/dev/null || true
  fi
done

# Create admin user
/opt/keycloak/bin/kcadm.sh create users -r $REALM -s username=admin -s email=admin@logisense.io -s emailVerified=true -s enabled=true -s firstName=Platform -s lastName=Administrator
/opt/keycloak/bin/kcadm.sh set-password -r $REALM --username admin --new-password '$DEFAULT_PASSWORD'
/opt/keycloak/bin/kcadm.sh add-roles -r $REALM --uusername admin --rolename PLATFORM_ADMIN 2>/dev/null || true

# Create manager user
/opt/keycloak/bin/kcadm.sh create users -r $REALM -s username=manager -s email=manager@logisense.io -s emailVerified=true -s enabled=true -s firstName=Facility -s lastName=Manager
/opt/keycloak/bin/kcadm.sh set-password -r $REALM --username manager --new-password '$DEFAULT_PASSWORD'
/opt/keycloak/bin/kcadm.sh add-roles -r $REALM --uusername manager --rolename FACILITY_MANAGER 2>/dev/null || true

# Create operator user
/opt/keycloak/bin/kcadm.sh create users -r $REALM -s username=operator -s email=operator@logisense.io -s emailVerified=true -s enabled=true -s firstName=Warehouse -s lastName=Operator
/opt/keycloak/bin/kcadm.sh set-password -r $REALM --username operator --new-password '$DEFAULT_PASSWORD'
/opt/keycloak/bin/kcadm.sh add-roles -r $REALM --uusername operator --rolename WAREHOUSE_OPERATOR 2>/dev/null || true

# Create analyst user
/opt/keycloak/bin/kcadm.sh create users -r $REALM -s username=analyst -s email=analyst@logisense.io -s emailVerified=true -s enabled=true -s firstName=Business -s lastName=Analyst
/opt/keycloak/bin/kcadm.sh set-password -r $REALM --username analyst --new-password '$DEFAULT_PASSWORD'
/opt/keycloak/bin/kcadm.sh add-roles -r $REALM --uusername analyst --rolename ANALYST_READ_ONLY 2>/dev/null || true
"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                    Keycloak Test Users Created                           ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
echo "║  admin     │ admin@logisense.io     │ PLATFORM_ADMIN                     ║"
echo "║  manager   │ manager@logisense.io   │ FACILITY_MANAGER                   ║"
echo "║  operator  │ operator@logisense.io  │ WAREHOUSE_OPERATOR                 ║"
echo "║  analyst   │ analyst@logisense.io   │ ANALYST_READ_ONLY                  ║"
echo "╠──────────────────────────────────────────────────────────────────────────╣"
echo "║  Password: $DEFAULT_PASSWORD                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
