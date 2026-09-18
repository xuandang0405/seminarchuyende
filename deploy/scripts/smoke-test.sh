#!/usr/bin/env bash
# ==============================================================================
# deploy/scripts/smoke-test.sh
# Automated Post-Deployment Verification & Smoke Test
# Usage: ./smoke-test.sh [TARGET_URL]
# Example: ./smoke-test.sh http://1.55.58.251:8000
# ==============================================================================
set -Eeuo pipefail

TARGET="${1:-http://127.0.0.1:8000}"
TARGET="${TARGET%/}"

echo "========================================================"
echo "   TOURVOICE QUẬN 4 - POST-DEPLOYMENT SMOKE TEST"
echo "   Target Base URL: ${TARGET}"
echo "========================================================"

FAILED=0

# Test 1: Health Check Endpoint
echo -n "[Test 1/5] Checking Backend Health (/api/v1/health)... "
HEALTH_RESP=$(curl -s -w "\n%{http_code}" "${TARGET}/api/v1/health" || echo -e "\n000")
HEALTH_STATUS=$(echo "${HEALTH_RESP}" | tail -n 1)
HEALTH_BODY=$(echo "${HEALTH_RESP}" | head -n -1)

if [ "${HEALTH_STATUS}" -eq 200 ]; then
    echo "✅ PASS (HTTP 200)"
else
    echo "❌ FAIL (HTTP ${HEALTH_STATUS}) Body: ${HEALTH_BODY}"
    FAILED=1
fi

# Test 2: Map Config Endpoint
echo -n "[Test 2/5] Checking Map Config (/api/v1/map/config)... "
MAP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${TARGET}/api/v1/map/config" || echo "000")
if [ "${MAP_STATUS}" -eq 200 ]; then
    echo "✅ PASS (HTTP 200)"
else
    echo "❌ FAIL (HTTP ${MAP_STATUS})"
    FAILED=1
fi

# Test 3: CORS Preflight OPTIONS on /api/v1/auth/login
echo -n "[Test 3/5] Testing CORS Preflight (OPTIONS /api/v1/auth/login)... "
OPTIONS_RESP=$(curl -s -i -X OPTIONS "${TARGET}/api/v1/auth/login" \
    -H "Origin: http://1.55.58.251" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: content-type, authorization, x-csrf-token" || true)

if echo "${OPTIONS_RESP}" | grep -qi "access-control-allow-origin"; then
    echo "✅ PASS (CORS Headers Present)"
else
    echo "❌ FAIL (Missing Access-Control-Allow-Origin header)"
    FAILED=1
fi

# Test 4: Static Client Portal
echo -n "[Test 4/5] Checking Client Web Portal (/client/)... "
CLIENT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${TARGET}/client/" || echo "000")
if [ "${CLIENT_STATUS}" -eq 200 ]; then
    echo "✅ PASS (HTTP 200)"
else
    echo "❌ FAIL (HTTP ${CLIENT_STATUS})"
    FAILED=1
fi

# Test 5: Verify admin.js does NOT contain http://localhost:8000
echo -n "[Test 5/5] Asserting Admin JS does not contain localhost:8000... "
ADMIN_JS=$(curl -s "${TARGET}/admin/admin.js" || true)
if echo "${ADMIN_JS}" | grep -q "const API_BASE = \"http://localhost:8000"; then
    echo "❌ FAIL: admin.js still has hardcoded localhost:8000!"
    FAILED=1
else
    echo "✅ PASS (No hardcoded localhost in admin.js)"
fi

echo "========================================================"
if [ "${FAILED}" -ne 0 ]; then
    echo "❌ SMOKE TEST FAILED! One or more tests did not pass."
    exit 1
else
    echo "✅ ALL SMOKE TESTS PASSED! Deployment is healthy & ready."
    exit 0
fi
