#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

export TOURVOICE_PORT="${TOURVOICE_PORT:-8080}"
export TOURVOICE_ENV_FILE="${TOURVOICE_ENV_FILE:-./env/.env.production}"
command_name="${1:-up}"
project=tourvoice
if [[ "$command_name" == demo || "$command_name" == admin-demo ]]; then project=tourvoice-demo; fi
compose=(docker compose -p "${TOURVOICE_PROJECT:-$project}" -f deploy/docker-compose.prod.yml)

command -v docker >/dev/null || { echo "Cần Docker Engine và Docker Compose v2." >&2; exit 1; }
docker compose version >/dev/null
docker info >/dev/null

case "$command_name" in
  demo)
    export TOURVOICE_ENV_FILE="./env/.env.demo"
    env_file="deploy/${TOURVOICE_ENV_FILE}"
    command -v openssl >/dev/null || { echo "Cần OpenSSL để tạo khóa demo." >&2; exit 1; }
    if [[ ! -f "$env_file" ]]; then
      umask 077
      secret=$(openssl rand -hex 32)
      offline_key=$(openssl rand -base64 32)
      (
        set -o noclobber
        cat > "$env_file" <<EOF
APP_ENV=development
DEBUG=false
ALLOW_MOCK_DATABASE=false
PAYMENT_MODE=mock
DATABASE_NAME=tourvoice_release_demo
PUBLIC_WEB_URL=http://localhost:$TOURVOICE_PORT
FRONTEND_URL=http://localhost:$TOURVOICE_PORT
FRONTEND_CALLBACK_URL=http://localhost:$TOURVOICE_PORT/auth/callback
TRUSTED_HOSTS=localhost,127.0.0.1
COOKIE_SECURE=false
SECRET_KEY=$secret
OFFLINE_LICENSE_PRIVATE_KEY=$offline_key
SUPERADMIN_BOOTSTRAP_MODE=disabled
EOF
      )
    fi
    "${compose[@]}" up --build -d --wait --wait-timeout 180
    "${compose[@]}" exec -T backend python -m demo.seed
    bash deploy/scripts/smoke-test.sh "http://127.0.0.1:$TOURVOICE_PORT"
    echo "Demo sẵn sàng tại http://localhost:$TOURVOICE_PORT/client/"
    echo "Tạo admin: bash deploy/scripts/deploy.sh admin-demo"
    ;;
  up)
    "${compose[@]}" up --build -d --wait --wait-timeout 180
    bash deploy/scripts/smoke-test.sh "http://127.0.0.1:$TOURVOICE_PORT"
    ;;
  admin|admin-demo)
    if [[ "$1" == admin-demo ]]; then
      export TOURVOICE_ENV_FILE="./env/.env.demo"
    fi
    read -rp "Email quản trị viên: " SUPERADMIN_EMAIL
    read -rsp "Mật khẩu mới (tối thiểu 12 ký tự): " SUPERADMIN_PASSWORD
    echo
    if [[ "$SUPERADMIN_EMAIL" != *@* || ${#SUPERADMIN_PASSWORD} -lt 12 ]]; then
      echo "Email hoặc mật khẩu không hợp lệ." >&2
      exit 1
    fi
    export SUPERADMIN_EMAIL SUPERADMIN_PASSWORD
    "${compose[@]}" run --rm --no-deps -T -e SUPERADMIN_EMAIL -e SUPERADMIN_PASSWORD \
      -e SUPERADMIN_BOOTSTRAP_MODE=create backend python - <<'PY'
import asyncio
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.db.bootstrap import bootstrap
from app.db.collections import COLLECTION_ADMIN_USERS

async def main():
    settings.validate_runtime()
    await connect_to_mongo()
    try:
        db = get_database()
        if await db[COLLECTION_ADMIN_USERS].find_one({"role": "super_admin"}):
            raise SystemExit("Đã có tài khoản quản trị tối cao.")
        await bootstrap(db)
        print("Đã tạo tài khoản quản trị tối cao.")
    finally:
        await close_mongo_connection()

asyncio.run(main())
PY
    ;;
  *)
    echo "Cách dùng: bash deploy/scripts/deploy.sh [demo|admin-demo|up|admin]" >&2
    exit 2
    ;;
esac
