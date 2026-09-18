#!/usr/bin/env bash
# ==============================================================================
# deploy/scripts/preflight.sh
# Checks host environment prerequisites prior to release deployment.
# ==============================================================================
set -Eeuo pipefail

echo "========================================================"
echo "   TOURVOICE QUẬN 4 - PREFLIGHT DEPLOYMENT AUDIT"
echo "========================================================"

FAILED=0

# 1. Check Python version
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -V 2>&1)
    echo "✅ Python installed: ${PY_VER}"
else
    echo "❌ Python3 is missing!"
    FAILED=1
fi

# 2. Check Nginx
if command -v nginx &>/dev/null; then
    NGINX_VER=$(nginx -v 2>&1)
    echo "✅ Nginx installed: ${NGINX_VER}"
else
    echo "⚠️ Nginx is not installed directly on host (skip if using Docker Compose)."
fi

# 3. Check port 80 & 8000 conflicts
if command -v netstat &>/dev/null; then
    echo "ℹ️ Active listening ports:"
    netstat -tlpn 2>/dev/null | grep -E ':(80|443|8000|27017)\b' || true
fi

# 4. Check Node.js for build guard
if command -v node &>/dev/null; then
    NODE_VER=$(node -v)
    echo "✅ Node.js installed: ${NODE_VER}"
else
    echo "⚠️ Node.js is missing. Required on local machine for client validation."
fi

# 5. Check MongoDB connectivity
if command -v mongosh &>/dev/null; then
    if mongosh --eval "db.runCommand({ ping: 1 })" --quiet &>/dev/null; then
        echo "✅ MongoDB is running and reachable."
    else
        echo "⚠️ MongoDB ping failed. Ensure mongod service is active."
    fi
fi

if [ "${FAILED}" -ne 0 ]; then
    echo -e "\n❌ Preflight checks failed! Please install missing prerequisites before deploying."
    exit 1
else
    echo -e "\n✅ All essential preflight checks completed successfully."
    exit 0
fi
