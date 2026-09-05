#!/usr/bin/env bash
# Start product Web (Mac / Linux). Keep this terminal open.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ""
echo "========================================"
echo "  产品需求梳理智能体 · 启动"
echo "========================================"
echo ""

PY="python3"
if [ -x "project/.venv/bin/python" ]; then
  PY="project/.venv/bin/python"
  echo "[OK] Using project/.venv"
else
  echo "[WARN] project/.venv not found. Run ./setup.sh first."
fi

if [ ! -f "project/.env" ]; then
  echo "[ERROR] Missing project/.env"
  echo "        cp project/.env.example project/.env  and set AGNES_API_KEY"
  exit 1
fi

# Free port 8765 if something is listening (best-effort)
if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -tiTCP:8765 -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "${PIDS}" ]; then
    echo "[INFO] Freeing port 8765 ..."
    # shellcheck disable=SC2086
    kill ${PIDS} 2>/dev/null || true
    sleep 1
  fi
fi

echo "Starting http://127.0.0.1:8765/ ..."
echo "Keep this terminal OPEN. Ctrl+C to stop."
echo ""

# Open browser after short delay (background)
(
  sleep 2
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:8765/" || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:8765/" || true
  fi
) &

exec "$PY" scripts/stage0_server.py --no-browser
