# Shared settings for setup.sh and deploy.sh. Source this file; do not run it.
#
#   PROJECT_ID   GCP project (required; falls back to the active gcloud project)
#   REGION       default us-central1 (us-west1, us-central1 and us-east1 have the free tier)
#   ZONE         default ${REGION}-a
#   DOMAIN       optional host name you own; default is <static-ip>.sslip.io

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "PROJECT_ID is not set. Export PROJECT_ID or run: gcloud config set project <id>" >&2
  exit 1
fi

REGION="${REGION:-us-central1}"
ZONE="${ZONE:-${REGION}-a}"

APP_NAME="${APP_NAME:-route53-clone}"
VM_NAME="${VM_NAME:-${APP_NAME}}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-micro}"
DISK_SIZE_GB="${DISK_SIZE_GB:-30}"
ADDRESS_NAME="${ADDRESS_NAME:-${APP_NAME}-ip}"
REPOSITORY="${REPOSITORY:-${APP_NAME}}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-${APP_NAME}-vm}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
BACKUP_BUCKET="${BACKUP_BUCKET:-${PROJECT_ID}-${APP_NAME}-backups}"

REGISTRY_HOST="${REGION}-docker.pkg.dev"
IMAGE_PREFIX="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}"
REMOTE_DIR="/srv/route53"

# Ask before anything that can cost money. ASSUME_YES=1 skips the questions.
confirm() {
  if [[ "${ASSUME_YES:-0}" == "1" ]]; then
    return 0
  fi
  read -r -p "$1 [y/N] " answer
  [[ "${answer}" =~ ^[Yy]$ ]]
}

log() {
  printf '\n==> %s\n' "$*"
}

static_ip() {
  gcloud compute addresses describe "${ADDRESS_NAME}" \
    --project "${PROJECT_ID}" --region "${REGION}" --format 'value(address)'
}

# The public host name: DOMAIN if given, otherwise the static IP through sslip.io.
site_address() {
  if [[ -n "${DOMAIN:-}" ]]; then
    echo "${DOMAIN}"
  else
    echo "$(static_ip | tr . -).sslip.io"
  fi
}
