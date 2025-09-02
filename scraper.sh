#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: $(basename "$0") [command]

Commands:
  -i, --init       Initialize and start database stack (Docker: Postgres + pgAdmin)
  -s, --start      Start local Python scraper in virtual environment
  -t, --test       Test download for a project dataset (version 1)
  -k, --kill       Stop and remove database containers
  -h, --help       Show this help

Environment:
  DATABASE_URL     e.g. postgresql://scraper:password@localhost:5432/roboflow_scraper
  ROBOFLOW_API_KEY Your Roboflow API key (also read from .env)
EOF
}

ensure_env() {
  if [[ -f "$ROOT_DIR/.env" ]]; then
    # shellcheck disable=SC2046
    export $(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ROOT_DIR/.env" | xargs -d '\n') || true
  fi
}

init_stack() {
  ensure_env
  echo "[+] Starting database stack (Docker Compose)"
  docker compose up -d
  echo "[+] Waiting for Postgres to become healthy..."
  sleep 5
  echo "[+] pgAdmin: http://localhost:5050 (admin@example.com / admin123)"
}

start_scraper() {
  ensure_env
  cd "$ROOT_DIR" || exit 1
  if [[ ! -d .venv ]]; then
    echo "[+] Creating virtual environment"
    python -m venv .venv
  fi
  # shellcheck disable=SC1091
  if [[ "$(uname -s)" == "Darwin" || "$(uname -s)" == "Linux" ]]; then
    source .venv/bin/activate
  else
    # On Git Bash, this will still work if python created Scripts/activate
    source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
  fi
  echo "[+] Installing Python dependencies"
  # Use the venv's python explicitly for pip so Windows doesn't complain
  if [[ -f .venv/Scripts/python.exe ]]; then
    .venv/Scripts/python.exe -m pip install -U pip
    .venv/Scripts/python.exe -m pip install -r requirements.txt
  else
    python -m pip install -U pip
    python -m pip install -r requirements.txt
  fi
  echo "[+] Installing Playwright browsers"
  python -m playwright install chromium
  echo "[+] Running scraper"
  python src/test_scraper.py
}

test_download() {
  ensure_env
  cd "$ROOT_DIR" || exit 1
  if [[ ! -d .venv ]]; then
    echo "[+] Creating virtual environment"
    python -m venv .venv
  fi
  # shellcheck disable=SC1091
  if [[ "$(uname -s)" == "Darwin" || "$(uname -s)" == "Linux" ]]; then
    source .venv/bin/activate
  else
    source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
  fi

  echo "[+] Ensuring Python dependencies for test"
  if [[ -f .venv/Scripts/python.exe ]]; then
    .venv/Scripts/python.exe -m pip install -U pip
    .venv/Scripts/python.exe -m pip install -r requirements.txt
  else
    python -m pip install -U pip
    python -m pip install -r requirements.txt
  fi

  local WORKSPACE_ID=""
  local PROJECT_ID=""

  # parse flags after -t/--test
  shift || true
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -w|--workspace)
        WORKSPACE_ID="$2"; shift 2 ;;
      -p|--project)
        PROJECT_ID="$2"; shift 2 ;;
      --)
        shift; break ;;
      -h|--help)
        echo "Usage: $(basename "$0") -t -w <workspace_id> -p <project_id>"; return 0 ;;
      *)
        echo "Unknown option for test: $1"; echo "Usage: $(basename "$0") -t -w <workspace_id> -p <project_id>"; return 1 ;;
    esac
  done

  if [[ -z "$WORKSPACE_ID" || -z "$PROJECT_ID" ]]; then
    echo "[-] Missing required flags."
    echo "Usage: $(basename "$0") -t -w <workspace_id> -p <project_id>"
    return 1
  fi

  if [[ -z "${ROBOFLOW_API_KEY:-}" ]]; then
    echo "[-] ROBOFLOW_API_KEY not set. Add it to .env or export it."
    return 1
  fi

  echo "[+] Testing dataset download for $WORKSPACE_ID/$PROJECT_ID (version 1)"
  python - "$WORKSPACE_ID" "$PROJECT_ID" <<'PYCODE'
import os
import sys
from pathlib import Path

workspace_id = sys.argv[1]
project_id = sys.argv[2]
api_key = os.getenv('ROBOFLOW_API_KEY')
if not api_key:
    print('ROBOFLOW_API_KEY not set')
    sys.exit(1)

try:
    from roboflow import Roboflow
except Exception as e:
    print(f'Failed to import roboflow: {e}')
    sys.exit(1)

download_root = Path('test_results/downloads')
download_root.mkdir(parents=True, exist_ok=True)
target_dir = download_root / f"{workspace_id}_{project_id}"
target_dir.mkdir(parents=True, exist_ok=True)

print(f"Connecting to Roboflow for {workspace_id}/{project_id}...")
rf = Roboflow(api_key=api_key)
try:
    project = rf.workspace(workspace_id).project(project_id)
    version = project.version(1)
    # Try multiple common formats for robustness
    candidate_formats = ['coco', 'yolov8', 'darknet', 'voc', 'folder']
    last_error = None
    for fmt in candidate_formats:
        try:
            print(f'Trying format: {fmt} ...')
            dataset = version.download(model_format=fmt)
            print('Download triggered successfully.')
            print(f'Format: {fmt}')
            print(f'Download location: {getattr(dataset, "location", "unknown")}')
            sys.exit(0)
        except Exception as e:
            last_error = e
            print(f'Format {fmt} failed: {e}')
            continue
    raise SystemExit(f'All formats failed. Last error: {last_error}')
except Exception as e:
    print(f'Failed to download dataset version 1: {e}')
    sys.exit(2)
PYCODE
}

kill_stack() {
  echo "[+] Stopping database containers"
  docker compose down
}

cmd="${1:-}" || true
case "$cmd" in
  -i|--init)
    init_stack
    ;;
  -s|--start)
    start_scraper
    ;;
  -t|--test)
    test_download "$@"
    ;;
  -k|--kill)
    kill_stack
    ;;
  -h|--help|*)
    usage
    ;;
esac


