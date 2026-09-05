#!/usr/bin/env bash
# Stage 1: create venv + install deps (Mac / Linux)
set -euo pipefail
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  Stage 1: setup Python environment"
echo "========================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found. Install Python 3.10+ first."
  exit 1
fi

cd project

if [ ! -x ".venv/bin/python" ]; then
  echo "Creating virtualenv .venv ..."
  python3 -m venv .venv
fi

echo "Installing packages ..."
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Checking imports ..."
python -c "import yaml, langgraph; print('[OK] yaml + langgraph')"

cd ..
echo ""
echo "[OK] Environment ready."
echo "Next: cp project/.env.example project/.env  and set AGNES_API_KEY"
echo "Then: ./start-with-ai.sh"
echo ""
