#!/usr/bin/env bash
# VM startup script (Debian 12). Runs as root on every boot and is safe to repeat:
# installs Docker with the compose plugin, adds swap, prepares the data directory and
# schedules the nightly backup.
set -euo pipefail

DATA_ROOT=/srv/route53
SWAP_FILE=/swapfile
SWAP_SIZE=2G
# Matches the unprivileged user in backend/Dockerfile.
BACKEND_UID=10001

metadata() {
  curl -sf -H 'Metadata-Flavor: Google' \
    "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1" || true
}

if ! command -v docker >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl gnupg sqlite3
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/debian $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
fi

# 1 GB of RAM is tight for Next.js + FastAPI + Caddy; swap keeps the OOM killer away.
if ! swapon --show | grep -q "${SWAP_FILE}"; then
  if [[ ! -f "${SWAP_FILE}" ]]; then
    fallocate -l "${SWAP_SIZE}" "${SWAP_FILE}"
    chmod 600 "${SWAP_FILE}"
    mkswap "${SWAP_FILE}"
  fi
  swapon "${SWAP_FILE}"
  grep -q "${SWAP_FILE}" /etc/fstab || echo "${SWAP_FILE} none swap sw 0 0" >> /etc/fstab
fi
sysctl -w vm.swappiness=10 >/dev/null

mkdir -p "${DATA_ROOT}/data" "${DATA_ROOT}/backups"
chown "${BACKEND_UID}:${BACKEND_UID}" "${DATA_ROOT}/data"

# Google's Debian images ship the Cloud CLI; install it if this image does not.
if ! command -v gcloud >/dev/null 2>&1; then
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    > /etc/apt/sources.list.d/google-cloud-sdk.list
  apt-get update
  apt-get install -y google-cloud-cli
fi

# Let Docker pull from Artifact Registry with the VM's service account.
REGISTRY_HOST="$(metadata registry-host)"
if [[ -n "${REGISTRY_HOST}" ]]; then
  gcloud auth configure-docker "${REGISTRY_HOST}" --quiet
fi

# Nightly online backup of the SQLite database to Cloud Storage. deploy.sh installs
# backup.sh; until the first deploy the job has nothing to run and does nothing.
BACKUP_BUCKET="$(metadata backup-bucket)"
if [[ -n "${BACKUP_BUCKET}" ]]; then
  cat > /etc/cron.d/route53-backup <<CRON
17 3 * * * root [ -x ${DATA_ROOT}/backup.sh ] && BACKUP_BUCKET=${BACKUP_BUCKET} ${DATA_ROOT}/backup.sh >> /var/log/route53-backup.log 2>&1
CRON
fi
