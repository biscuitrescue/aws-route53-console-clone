#!/usr/bin/env bash
# Local development in one command: migrate and seed the database, then run the API on
# :8000 and the web app on :3000 until Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")"

(
  cd backend
  uv sync --quiet
  uv run alembic upgrade head
  uv run python -m app.seed
)
[ -d frontend/node_modules ] || (cd frontend && npm install)

trap 'kill 0' EXIT
(cd backend && exec uv run uvicorn --factory app.main:create_app --reload --port 8000) &
(cd frontend && exec npm run dev) &
wait
