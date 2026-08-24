#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
cd "$project_dir"

cleanup() {
  [[ -n "${api_pid:-}" ]] && kill "$api_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

uv run uvicorn shadowlearn.main:app --app-dir backend --host 127.0.0.1 --port 8420 --reload &
api_pid=$!
cd frontend
npm run dev

