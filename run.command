#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "Falta uv. Instalalo con: brew install uv"
  read -p "Enter para cerrar..."
  exit 1
fi

uv sync
uv run uvicorn src.agent.ui:app --port 8000 &
sleep 2
open http://127.0.0.1:8000
wait
