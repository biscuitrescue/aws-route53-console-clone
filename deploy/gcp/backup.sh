#!/usr/bin/env bash
# Back up the live SQLite database to Cloud Storage. Runs on the VM from cron.
#
# Uses SQLite's online backup API (".backup"), which takes a consistent snapshot while
# the application keeps writing. Never copy the database file directly: with WAL enabled
# a raw copy can miss committed transactions or be corrupt.
set -euo pipefail

: "${BACKUP_BUCKET:?BACKUP_BUCKET is required}"
DATABASE="${DATABASE:-/srv/route53/data/route53.db}"
WORK_DIR="${WORK_DIR:-/srv/route53/backups}"
KEEP_LOCAL="${KEEP_LOCAL:-3}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
snapshot="${WORK_DIR}/route53-${stamp}.db"

sqlite3 "${DATABASE}" ".backup '${snapshot}'"
sqlite3 "${snapshot}" "PRAGMA integrity_check;" | grep -qx ok
gzip "${snapshot}"
gcloud storage cp "${snapshot}.gz" "gs://${BACKUP_BUCKET}/route53-${stamp}.db.gz"

# Keep only the newest few snapshots on the VM; the bucket's lifecycle rule prunes the rest.
ls -1t "${WORK_DIR}"/route53-*.db.gz | tail -n "+$((KEEP_LOCAL + 1))" | xargs -r rm -f
echo "$(date -u +%FT%TZ) backed up ${DATABASE} to gs://${BACKUP_BUCKET}/route53-${stamp}.db.gz"
