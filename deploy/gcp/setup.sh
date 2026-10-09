#!/usr/bin/env bash
# One-time infrastructure for the hosted demo. Safe to run again: every step checks
# whether its resource already exists.
#
#   PROJECT_ID=my-project REGION=us-central1 ZONE=us-central1-a ./deploy/gcp/setup.sh
#
# Creates: Artifact Registry repository, a service account for the VM, a static external
# IP, firewall rules for web traffic and IAP SSH, a backup bucket (unless
# ENABLE_BACKUPS=0), and the Compute Engine VM. Asks before each billable resource.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deploy/gcp/config.sh
source "${HERE}/config.sh"

ENABLE_BACKUPS="${ENABLE_BACKUPS:-1}"
NETWORK="${NETWORK:-default}"
IAP_RANGE="35.235.240.0/20"

exists() {
  "$@" >/dev/null 2>&1
}

log "Project ${PROJECT_ID}, region ${REGION}, zone ${ZONE}"

log "Enabling APIs (Compute Engine, Artifact Registry, Cloud Build, IAP)"
gcloud services enable --project "${PROJECT_ID}" \
  compute.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  iap.googleapis.com

log "Artifact Registry repository ${REPOSITORY}"
if ! exists gcloud artifacts repositories describe "${REPOSITORY}" \
  --project "${PROJECT_ID}" --location "${REGION}"; then
  confirm "Create Artifact Registry repository ${REPOSITORY}? (0.5 GB of storage is free)" || exit 1
  gcloud artifacts repositories create "${REPOSITORY}" \
    --project "${PROJECT_ID}" --location "${REGION}" --repository-format docker \
    --description "Images for the Route 53 console clone"
fi

log "Service account ${SERVICE_ACCOUNT}"
if ! exists gcloud iam service-accounts describe "${SERVICE_ACCOUNT}" --project "${PROJECT_ID}"; then
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --project "${PROJECT_ID}" --display-name "Route 53 clone VM"
fi
# The VM only needs to pull its images and write logs.
gcloud artifacts repositories add-iam-policy-binding "${REPOSITORY}" \
  --project "${PROJECT_ID}" --location "${REGION}" \
  --member "serviceAccount:${SERVICE_ACCOUNT}" --role roles/artifactregistry.reader >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member "serviceAccount:${SERVICE_ACCOUNT}" --role roles/logging.logWriter \
  --condition None >/dev/null

if [[ "${ENABLE_BACKUPS}" == "1" ]]; then
  log "Backup bucket gs://${BACKUP_BUCKET}"
  if ! exists gcloud storage buckets describe "gs://${BACKUP_BUCKET}" --project "${PROJECT_ID}"; then
    confirm "Create backup bucket gs://${BACKUP_BUCKET}? (5 GB of regional storage is free)" || exit 1
    gcloud storage buckets create "gs://${BACKUP_BUCKET}" \
      --project "${PROJECT_ID}" --location "${REGION}" --uniform-bucket-level-access
    lifecycle="$(mktemp)"
    echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":30}}]}' > "${lifecycle}"
    gcloud storage buckets update "gs://${BACKUP_BUCKET}" --lifecycle-file "${lifecycle}"
    rm -f "${lifecycle}"
  fi
  # Upload needs create, and `gcloud storage cp` also reads the object's metadata.
  for role in roles/storage.objectCreator roles/storage.objectViewer; do
    gcloud storage buckets add-iam-policy-binding "gs://${BACKUP_BUCKET}" \
      --member "serviceAccount:${SERVICE_ACCOUNT}" --role "${role}" >/dev/null
  done
fi

log "Static external IP ${ADDRESS_NAME}"
if ! exists gcloud compute addresses describe "${ADDRESS_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}"; then
  confirm "Reserve a static external IPv4 address? (billed hourly; see the README)" || exit 1
  gcloud compute addresses create "${ADDRESS_NAME}" \
    --project "${PROJECT_ID}" --region "${REGION}" --network-tier STANDARD
fi

log "Firewall rules"
if ! exists gcloud compute firewall-rules describe "${APP_NAME}-allow-web" --project "${PROJECT_ID}"; then
  gcloud compute firewall-rules create "${APP_NAME}-allow-web" \
    --project "${PROJECT_ID}" --network "${NETWORK}" --direction INGRESS \
    --allow tcp:80,tcp:443,udp:443 --source-ranges 0.0.0.0/0 \
    --target-tags http-server,https-server \
    --description "Web traffic to the Route 53 clone"
fi
if ! exists gcloud compute firewall-rules describe "${APP_NAME}-allow-iap-ssh" --project "${PROJECT_ID}"; then
  gcloud compute firewall-rules create "${APP_NAME}-allow-iap-ssh" \
    --project "${PROJECT_ID}" --network "${NETWORK}" --direction INGRESS \
    --allow tcp:22 --source-ranges "${IAP_RANGE}" --target-tags "${APP_NAME}" \
    --description "SSH only through Identity-Aware Proxy"
fi
if exists gcloud compute firewall-rules describe default-allow-ssh --project "${PROJECT_ID}"; then
  echo "Note: the default-allow-ssh rule opens port 22 to the internet for this network."
  echo "      SSH here goes through IAP, so you can delete it:"
  echo "      gcloud compute firewall-rules delete default-allow-ssh --project ${PROJECT_ID}"
fi

log "VM ${VM_NAME} (${MACHINE_TYPE}, Debian 12, ${DISK_SIZE_GB} GB standard disk)"
if ! exists gcloud compute instances describe "${VM_NAME}" --project "${PROJECT_ID}" --zone "${ZONE}"; then
  confirm "Create the ${MACHINE_TYPE} VM ${VM_NAME} in ${ZONE}?" || exit 1
  metadata="registry-host=${REGISTRY_HOST}"
  if [[ "${ENABLE_BACKUPS}" == "1" ]]; then
    metadata+=",backup-bucket=${BACKUP_BUCKET}"
  fi
  gcloud compute instances create "${VM_NAME}" \
    --project "${PROJECT_ID}" --zone "${ZONE}" --machine-type "${MACHINE_TYPE}" \
    --image-family debian-12 --image-project debian-cloud \
    --boot-disk-size "${DISK_SIZE_GB}GB" --boot-disk-type pd-standard \
    --address "$(static_ip)" --network-tier STANDARD --network "${NETWORK}" \
    --tags "http-server,https-server,${APP_NAME}" \
    --service-account "${SERVICE_ACCOUNT}" --scopes cloud-platform \
    --shielded-secure-boot \
    --metadata "${metadata}" \
    --metadata-from-file "startup-script=${HERE}/startup.sh"
fi

log "Done"
echo "VM address:  $(static_ip)"
echo "Site:        https://$(site_address)"
echo "Next:        ./deploy/gcp/deploy.sh   (the startup script needs about two minutes"
echo "             after the VM is created to finish installing Docker)"
