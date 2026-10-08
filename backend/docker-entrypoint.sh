#!/bin/sh
# Bring the database up to date, make sure the demo data exists, then serve.
set -eu

alembic upgrade head
python -m app.seed

# One worker: SQLite allows a single writer and the demo VM has 1 GB of RAM.
exec uvicorn --factory app.main:create_app \
    --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips '*'
