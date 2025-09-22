#!/usr/bin/env bash
# Simple deploy helper for backend (to be run on the server inside the repo)
# Assumptions:
# - This script is executed from the repository root or from scripts/ (it resolves repo root)
# - If a systemd service named 'songlab-backend' exists, it will try to restart it with sudo
# - Otherwise it will attempt to restart a uvicorn process using the project's venv

set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

echo "Deploy helper running in: $ROOT_DIR"

echo "Pulling latest code from git..."
git pull --ff-only || { echo "git pull failed - please resolve manually"; exit 2; }

# If a venv exists, try to install requirements
if [ -d ".venv_debug" ] && [ -x ".venv_debug/bin/python" ]; then
  echo "Found .venv_debug - installing requirements into it"
  . .venv_debug/bin/activate
  pip install --upgrade pip
  if [ -f requirements.txt ]; then
    pip install -r requirements.txt
  fi
  deactivate
elif [ -x "/usr/bin/python3" ]; then
  echo "No .venv_debug found - skipping venv install. Ensure dependencies are installed."
fi

echo "Attempting to restart systemd service 'songlab-backend' (if present)"
if sudo systemctl list-units --type=service --all | grep -q songlab-backend; then
  sudo systemctl restart songlab-backend
  sudo systemctl status --no-pager songlab-backend || true
  echo "systemd service restart attempted. Check status above."
else
  echo "Systemd unit 'songlab-backend' not found. Will attempt to restart uvicorn processes manually."
  # Kill any uvicorn running on the expected ports and restart using venv python if available
  pkill -f "uvicorn.*main_v2:app" || true
  sleep 1
  if [ -x ".venv_debug/bin/python" ]; then
    nohup .venv_debug/bin/python -m uvicorn main_v2:app --host 127.0.0.1 --port 8002 --log-level info > uvicorn_debug.log 2>&1 &
    echo "Started uvicorn with .venv_debug/bin/python, logs -> uvicorn_debug.log"
  else
    nohup python3 -m uvicorn main_v2:app --host 127.0.0.1 --port 8002 --log-level info > uvicorn_debug.log 2>&1 &
    echo "Started uvicorn with system python, logs -> uvicorn_debug.log"
  fi
fi

echo "Tail last 40 lines of uvicorn_debug.log (if exists):"
sleep 1
if [ -f uvicorn_debug.log ]; then
  tail -n 40 uvicorn_debug.log || true
else
  echo "No uvicorn_debug.log found in repo root"
fi

echo "Deploy helper finished."
