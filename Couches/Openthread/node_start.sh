#!/usr/bin/env bash
set -euo pipefail

NODE_NAME=${NODE_NAME:-node}
NODE_ID=${NODE_ID:-1}
NODE_IF=${NODE_IF:-wpan0}
OT_STATE_DIR=${OT_STATE_DIR:-/ot_state}
OT_REQUIRED=${OT_REQUIRED:-0}
DATASET_CHANNEL=${DATASET_CHANNEL:-15}
DATASET_PANID=${DATASET_PANID:-0x1234}
DATASET_EXTPANID=${DATASET_EXTPANID:-dead00beef00cafe}
DATASET_KEY=${DATASET_KEY:-00112233445566778899aabbccddeeff}
DATASET_NAME=${DATASET_NAME:-ZolisNet}

mkdir -p "$OT_STATE_DIR"
ADDR_FILE="$OT_STATE_DIR/${NODE_NAME}.addr"
# Prevent stale addresses from previous runs when the OT stack is not available.
rm -f "$ADDR_FILE"

start_daemon() {
  rm -f /tmp/ot-daemon.log
  ot-daemon -I "$NODE_IF" "spinel+hdlc+forkpty:///usr/local/bin/ot-rcp?forkpty-arg=${NODE_ID}" > /tmp/ot-daemon.log 2>&1 &
  OT_DAEMON_PID=$!
}

stop_daemon() {
  if [ -n "${OT_DAEMON_PID:-}" ] && kill -0 "$OT_DAEMON_PID" >/dev/null 2>&1; then
    kill "$OT_DAEMON_PID" || true
    wait "$OT_DAEMON_PID" || true
  fi
}

trap stop_daemon EXIT

ready=false
for attempt in $(seq 1 5); do
  start_daemon
  for _ in $(seq 1 60); do
    if ot-ctl -I "$NODE_IF" state >/dev/null 2>&1; then
      ready=true
      break
    fi
    sleep 0.5
  done
  if [ "$ready" = true ]; then
    break
  fi
  stop_daemon
  sleep 1
done

if [ "$ready" != true ]; then
  echo "ot-ctl is not ready after retries for NODE_NAME=${NODE_NAME} NODE_ID=${NODE_ID} NODE_IF=${NODE_IF}"
  echo "ot-daemon log follows:"
  cat /tmp/ot-daemon.log || true
  if [ "$OT_REQUIRED" = "1" ]; then
    exit 1
  fi
  rm -f "$ADDR_FILE"
  echo "Proceeding without OpenThread session (OT_REQUIRED=0)."
  if [ $# -gt 0 ]; then
    exec "$@"
  fi
  sleep infinity
fi

# Configure dataset
ot-ctl -I "$NODE_IF" dataset init new >/dev/null
ot-ctl -I "$NODE_IF" dataset networkname "$DATASET_NAME" >/dev/null
ot-ctl -I "$NODE_IF" dataset channel "$DATASET_CHANNEL" >/dev/null
ot-ctl -I "$NODE_IF" dataset panid "$DATASET_PANID" >/dev/null
ot-ctl -I "$NODE_IF" dataset extpanid "$DATASET_EXTPANID" >/dev/null
ot-ctl -I "$NODE_IF" dataset networkkey "$DATASET_KEY" >/dev/null
ot-ctl -I "$NODE_IF" dataset commit active >/dev/null

ot-ctl -I "$NODE_IF" ifconfig up >/dev/null
ot-ctl -I "$NODE_IF" thread start >/dev/null

# Wait until attached
for _ in $(seq 1 30); do
  state=$(ot-ctl -I "$NODE_IF" state 2>/dev/null || true)
  if [ "$state" = "leader" ] || [ "$state" = "router" ] || [ "$state" = "child" ]; then
    break
  fi
  sleep 0.5
done

# Save first ULA address
addr=$(ot-ctl -I "$NODE_IF" ipaddr | awk '/^fd/{print $1; exit}')
if [ -n "${addr}" ]; then
  echo "$addr" > "$ADDR_FILE"
else
  rm -f "$ADDR_FILE"
fi

# Execute service command
if [ $# -gt 0 ]; then
  exec "$@"
fi

# Default: keep container alive
sleep infinity
