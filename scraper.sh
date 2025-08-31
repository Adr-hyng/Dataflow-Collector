#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: $(basename "$0") [command]

Commands:
  -i, --init       Initialize and start database stack (Docker: Postgres + pgAdmin)
  -s, --start      Start local Python scraper in virtual environment
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
  -k|--kill)
    kill_stack
    ;;
  -h|--help|*)
    usage
    ;;
esac


