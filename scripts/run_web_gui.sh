#!/usr/bin/env bash
# Start the NJIT Thesis Auditor web UI via uvicorn.
# Usage: ./scripts/run_web_gui.sh [host [port]]
#   HOST defaults to 0.0.0.0 (all interfaces)
#   PORT defaults to 8000
# Environment variables:
#   NJIT_AUDITOR_WEB_RUNTIME_DIR  — runtime upload/report directory (default: .runtime/web_audits)
#   NJIT_AUDITOR_WEB_MAX_UPLOAD_MB — max upload size in MB (default: 50)
#   NJIT_AUDITOR_WEB_JOB_TTL_SECONDS — completed job retention in seconds (default: 86400)
set -euo pipefail
HOST="${1:-${NJIT_AUDITOR_WEB_HOST:-0.0.0.0}}"
PORT="${2:-${NJIT_AUDITOR_WEB_PORT:-8000}}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
echo "Starting NJIT Thesis Auditor web UI..."
echo "  Host:        $HOST"
echo "  Port:        $PORT"
echo "  Runtime dir: ${NJIT_AUDITOR_WEB_RUNTIME_DIR:-.runtime/web_audits}"
echo "  Press Ctrl-C to stop."
exec python -m uvicorn njit_auditor.web_app:app --host "$HOST" --port "$PORT"
