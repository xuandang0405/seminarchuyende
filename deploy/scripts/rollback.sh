#!/usr/bin/env bash
# ==============================================================================
# deploy/scripts/rollback.sh
# Emergency Rollback to Previous Stable Release
# ==============================================================================
set -Eeuo pipefail

DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/tour-guide}"
RELEASES_DIR="${DEPLOY_ROOT}/releases"

echo "========================================================"
echo "   TOURVOICE QUẬN 4 - EMERGENCY ROLLBACK RUNNER"
echo "========================================================"

if [ ! -d "${RELEASES_DIR}" ]; then
    echo "❌ Releases directory not found: ${RELEASES_DIR}"
    exit 1
fi

# Find releases sorted chronologically
RELEASES=($(ls -1d "${RELEASES_DIR}"/* 2>/dev/null | sort -r))

if [ "${#RELEASES[@]}" -lt 2 ]; then
    echo "❌ Cannot rollback: fewer than 2 releases exist in ${RELEASES_DIR}!"
    exit 1
fi

CURRENT_TARGET="$(readlink -f "${DEPLOY_ROOT}/current" || echo "")"
PREV_RELEASE=""

for r in "${RELEASES[@]}"; do
    if [ "$r" != "${CURRENT_TARGET}" ]; then
        PREV_RELEASE="$r"
        break
    fi
done

if [ -z "${PREV_RELEASE}" ]; then
    echo "❌ Failed to identify previous release candidate."
    exit 1
fi

echo "Current Release  : ${CURRENT_TARGET}"
echo "Rollback Target  : ${PREV_RELEASE}"

# Switch symlink
ln -sfn "${PREV_RELEASE}" "${DEPLOY_ROOT}/current"
echo "✅ Symlink switched to: ${PREV_RELEASE}"

# Restart backend service
if command -v systemctl &>/dev/null; then
    echo "Restarting service..."
    sudo systemctl restart tour-guide-api || true
fi

# Run smoke test on rolled back version
echo -e "\nRunning smoke test on rolled back release..."
bash "${PREV_RELEASE}/deploy/scripts/smoke-test.sh" "http://127.0.0.1:8000"

echo -e "\n========================================================"
echo "   🎉 ROLLBACK COMPLETED SUCCESSFULLY"
echo "========================================================"
