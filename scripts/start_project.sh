#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SERVICES=(
  db
  mqtt_broker
  coap-gps
  coap-batt
  coap-temp
  coap-leader
  coap-routeur
  backend
  frontend
)

BUILD=0
FOLLOW_LOGS=0
STRICT_THREAD=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/start_project.sh [options]

Options:
  --build           Rebuild images and force recreate containers.
  --logs            Follow key logs after startup.
  --strict-thread   Force OpenThread strict mode (IPv6 only).
  -h, --help        Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build)
      BUILD=1
      shift
      ;;
    --logs)
      FOLLOW_LOGS=1
      shift
      ;;
    --strict-thread)
      STRICT_THREAD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker command not found. Install/enable Docker first."
  exit 1
fi

OT_REQUIRED="${ZOLIS_OT_REQUIRED:-0}"
THREAD_STRICT="${ZOLIS_STRICT_THREAD:-0}"

if [[ "$STRICT_THREAD" -eq 1 ]]; then
  OT_REQUIRED=1
  THREAD_STRICT=1
fi

UP_ARGS=(up -d)
if [[ "$BUILD" -eq 1 ]]; then
  UP_ARGS=(up -d --build --force-recreate)
fi

echo "Starting Zolis with ZOLIS_OT_REQUIRED=${OT_REQUIRED} ZOLIS_STRICT_THREAD=${THREAD_STRICT}"
env ZOLIS_OT_REQUIRED="$OT_REQUIRED" ZOLIS_STRICT_THREAD="$THREAD_STRICT" \
  docker compose "${UP_ARGS[@]}" "${SERVICES[@]}"

docker compose ps

echo
echo "Frontend: http://127.0.0.1:5000"
echo "Tip: curl -X POST http://127.0.0.1:5000/api/backend/collect"

if [[ "$FOLLOW_LOGS" -eq 1 ]]; then
  docker compose logs -f backend frontend coap-routeur coap-leader
fi
