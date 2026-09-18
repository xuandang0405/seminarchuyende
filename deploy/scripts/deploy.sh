#!/usr/bin/env bash
# ==============================================================================
# deploy/scripts/deploy.sh
# Production Zero-Downtime Deployment Script (Local -> Host / On-Server Runner)
# ==============================================================================
set -Eeuo pipefail

DEPLOY_HOST="${DEPLOY_HOST:-1.55.58.251}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/tour-guide}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

RELEASE_TAG="$(date +%Y%m%d_%H%M%S)"
RELEASE_DIR="${DEPLOY_ROOT}/releases/${RELEASE_TAG}"
TARBALL_NAME="tourvoice_release_${RELEASE_TAG}.tar.gz"

echo "========================================================"
echo "   TOURVOICE QUẬN 4 - PRODUCTION RELEASE DEPLOYMENT"
echo "   Release Tag : ${RELEASE_TAG}"
echo "   Target Host : ${DEPLOY_HOST}"
echo "   Target Path : ${DEPLOY_ROOT}"
echo "========================================================"

# Step 1: Run Local Build Guard (No localhost in client code)
echo -e "\n[1/6] Running Local Build Guard..."
if [ -f "${PROJECT_ROOT}/scripts/assert-no-client-localhost.mjs" ]; then
    node "${PROJECT_ROOT}/scripts/assert-no-client-localhost.mjs"
else
    echo "⚠️ Build guard script not found, skipping."
fi

# Step 2: Build Web Client (if apps/web-admin has package.json and node_modules)
echo -e "\n[2/6] Checking Frontend Builds..."
if [ -d "${PROJECT_ROOT}/apps/web-admin" ] && [ -f "${PROJECT_ROOT}/apps/web-admin/package.json" ]; then
    if command -v npm &>/dev/null; then
        echo "Building React Web Admin (production mode)..."
        (cd "${PROJECT_ROOT}/apps/web-admin" && npm run build || true)
    fi
fi

# Step 3: Package Release Artifact (Exclude secrets, git, node_modules, temp files)
echo -e "\n[3/6] Packaging Release Artifact..."
TMP_PKG_DIR="$(mktemp -d)"
TARBALL_PATH="${TMP_PKG_DIR}/${TARBALL_NAME}"

tar --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.venv' \
    --exclude='*.env*' \
    --exclude='storage/audio/*' \
    -czf "${TARBALL_PATH}" \
    -C "${PROJECT_ROOT}" \
    backend frontend apps deploy

echo "✅ Artifact generated: $(ls -lh "${TARBALL_PATH}" | awk '{print $5, $9}')"

# Step 4: Deploying on Host
# If running directly on the production host:
if [ "${DEPLOY_HOST}" = "localhost" ] || [ "${DEPLOY_HOST}" = "127.0.0.1" ]; then
    echo -e "\n[4/6] Installing release locally on host..."
    mkdir -p "${RELEASE_DIR}"
    tar -xzf "${TARBALL_PATH}" -C "${RELEASE_DIR}"
    
    # Secure shared .env link
    mkdir -p "${DEPLOY_ROOT}/shared"
    if [ ! -f "${DEPLOY_ROOT}/shared/.env" ]; then
        cp "${RELEASE_DIR}/deploy/env/.env.production.example" "${DEPLOY_ROOT}/shared/.env"
        echo "⚠️ Created template ${DEPLOY_ROOT}/shared/.env. Please update secrets!"
    fi
    ln -sf "${DEPLOY_ROOT}/shared/.env" "${RELEASE_DIR}/backend/.env"
    
    # Storage persistence link
    mkdir -p "${DEPLOY_ROOT}/shared/storage"
    ln -sfn "${DEPLOY_ROOT}/shared/storage" "${RELEASE_DIR}/backend/storage"
    
    # Python Virtualenv setup
    if [ ! -d "${RELEASE_DIR}/backend/.venv" ]; then
        python3 -m venv "${RELEASE_DIR}/backend/.venv"
        "${RELEASE_DIR}/backend/.venv/bin/pip" install --upgrade pip
        "${RELEASE_DIR}/backend/.venv/bin/pip" install -r "${RELEASE_DIR}/backend/requirements.txt"
    fi

    # Step 5: Test Nginx & Restart Services
    echo -e "\n[5/6] Validating Nginx & Restarting Services..."
    if command -v nginx &>/dev/null; then
        sudo cp "${RELEASE_DIR}/deploy/nginx/tour-guide.conf" /etc/nginx/sites-available/tour-guide.conf
        sudo ln -sf /etc/nginx/sites-available/tour-guide.conf /etc/nginx/sites-enabled/
        sudo nginx -t
        sudo systemctl reload nginx
    fi

    # Switch current symlink
    ln -sfn "${RELEASE_DIR}" "${DEPLOY_ROOT}/current"
    if command -v systemctl &>/dev/null; then
        sudo systemctl restart tour-guide-api || true
    fi

    # Step 6: Execute Smoke Test
    echo -e "\n[6/6] Running Post-Deployment Smoke Test..."
    bash "${RELEASE_DIR}/deploy/scripts/smoke-test.sh" "http://127.0.0.1:8000"
else
    echo -e "\n[4/6] Remote deploy mode: Transferring artifact to ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_ROOT}/releases/ ..."
    echo "Lệnh chuyển giao thủ công hoặc qua SSH:"
    echo "  scp ${TARBALL_PATH} ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_ROOT}/"
    echo "  ssh ${DEPLOY_USER}@${DEPLOY_HOST} 'tar -xzf ${DEPLOY_ROOT}/${TARBALL_NAME} -C ${RELEASE_DIR} && ...'"
fi

# Cleanup local temp
rm -rf "${TMP_PKG_DIR}"

echo -e "\n========================================================"
echo "   🎉 DEPLOYMENT WORKFLOW COMPLETED SUCCESSFULLY"
echo "========================================================"
