#!/usr/bin/env bash
# Start the NeighborhoodIQ monorepo (local dev or Docker).
# Usage: ./scripts/start.sh [local|docker] [--install]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-local}"
INSTALL="${2:-}"

ensure_env() {
  if [[ ! -f "$ROOT/.env" ]]; then
    echo "==> Creating .env from .env.example"
    cp "$ROOT/.env.example" "$ROOT/.env"
  fi
}

ensure_api_venv() {
  local api_dir="$ROOT/apps/api"
  local venv_python="$api_dir/.venv/bin/python"

  if [[ ! -x "$venv_python" ]]; then
    echo "==> Creating Python virtual environment (apps/api/.venv)"
    (cd "$api_dir" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)
  elif [[ "$INSTALL" == "--install" ]]; then
    echo "==> Installing/updating API dependencies"
    (cd "$api_dir" && .venv/bin/pip install -r requirements.txt)
  fi
}

ensure_web_deps() {
  if [[ ! -d "$ROOT/apps/web/node_modules" || "$INSTALL" == "--install" ]]; then
    echo "==> Installing web dependencies (apps/web)"
    (cd "$ROOT/apps/web" && npm install)
  fi
}

ensure_root_deps() {
  if [[ ! -d "$ROOT/node_modules" || "$INSTALL" == "--install" ]]; then
    echo "==> Installing root dev dependencies (concurrently)"
    (cd "$ROOT" && npm install)
  fi
}

start_local() {
  ensure_env
  ensure_api_venv
  ensure_web_deps
  ensure_root_deps

  echo ""
  echo "NeighborhoodIQ - local dev"
  echo "  Web:  http://localhost:3000"
  echo "  API:  http://localhost:8000"
  echo "  Docs: http://localhost:8000/api/docs"
  echo ""
  echo "Press Ctrl+C to stop both services."
  echo ""

  cd "$ROOT"
  npm run dev
}

start_docker() {
  ensure_env
  command -v docker >/dev/null 2>&1 || {
    echo "Docker is not installed. Use: ./scripts/start.sh local"
    exit 1
  }
  echo "==> Starting Docker Compose stack"
  cd "$ROOT"
  docker compose up --build
}

case "$MODE" in
  local) start_local ;;
  docker) start_docker ;;
  *)
    echo "Usage: $0 [local|docker] [--install]"
    exit 1
    ;;
esac
