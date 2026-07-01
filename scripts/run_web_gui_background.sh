#!/usr/bin/env bash
# Start the NJIT Thesis Auditor web UI in the background with log capture.
# Usage: ./scripts/run_web_gui_background.sh [host [port]]
# Stops any existing listener on the target port first.
set -euo pipefail
HOST="${1:-${NJIT_AUDITOR_WEB_HOST:-0.0.0.0}}"
PORT="${2:-${NJIT_AUDITOR_WEB_PORT:-8000}}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
export PYTHONPATH="${PYTHONPATH:-$REPO_DIR/src}"
export NJIT_AUDITOR_WEB_RUNTIME_DIR="${NJIT_AUDITOR_WEB_RUNTIME_DIR:-$REPO_DIR/.runtime/web_audits}"
mkdir -p "$NJIT_AUDITOR_WEB_RUNTIME_DIR" "$REPO_DIR/.runtime"
LOG_FILE="$REPO_DIR/.runtime/uvicorn-${PORT}.log"
PID_FILE="$REPO_DIR/.runtime/uvicorn-${PORT}.pid"

if command -v ss >/dev/null 2>&1; then
  OLD_PID="$(ss -tlnp 2>/dev/null | rg ":${PORT}\\b" | rg -o 'pid=[0-9]+' | head -1 | cut -d= -f2 || true)"
  if [[ -n "${OLD_PID:-}" ]]; then
    echo "Stopping existing listener on port ${PORT} (pid ${OLD_PID})"
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
fi

nohup python -m uvicorn njit_auditor.web_app:app \
  --host "$HOST" \
  --port "$PORT" \
  >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
sleep 1
if curl -sf "http://127.0.0.1:${PORT}/healthz" >/dev/null; then
  echo "Web UI running on http://${HOST}:${PORT} (pid $(cat "$PID_FILE"))"
  echo "Log: $LOG_FILE"
else
  echo "Server failed health check. See $LOG_FILE" >&2
  tail -30 "$LOG_FILE" >&2 || true
  exit 1
fi
