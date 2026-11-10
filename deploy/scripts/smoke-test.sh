#!/usr/bin/env bash
set -Eeuo pipefail
PYTHON="${SMOKE_PYTHON:-python3}"
TARGET="${1:-http://127.0.0.1:8000}"
TARGET="${TARGET%/}"
check() {
  local path="$1" expected="$2" actual
  actual=$(curl --max-time 15 -sS -o /dev/null -w "%{http_code}" "${TARGET}${path}")
  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL $path: HTTP $actual (expected $expected)" >&2
    exit 1
  fi
  echo "PASS $path"
}
curl --fail --max-time 15 -sS "${TARGET}/api/v1/health" |
  "$PYTHON" -c 'import json,sys; d=json.load(sys.stdin); assert d["status"]=="healthy" and d["database"]["status"]=="connected" and d["mock_database"] is False'
check /client/ 200
check /admin/login 200
check /owner/ 200
check /sw.js 200
check /static/maps/packs/current/manifest.json 200
check /api/v1/analytics/live 401
check /api/v1/map/config 200
check /api/v1/payments/my-orders 401
check /api/v1/payments/orders 401
check /storage/audio/private.mp3 403
curl --fail --max-time 15 -sS "${TARGET}/client/" |
  "$PYTHON" -c 'import sys; s=sys.stdin.read(); assert "id=\"root\"" in s and "/assets/" in s, "Missing compiled React app"'
echo "PASS: readiness, compiled client, protected orders and media"
