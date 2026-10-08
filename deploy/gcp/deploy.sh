#!/usr/bin/env bash
# Build both images, roll them out on the VM and smoke-test the live site.
#
#   PROJECT_ID=my-project DEMO_PASSWORD='...' ./deploy/gcp/deploy.sh
#
#   BUILD=cloud   (default) build with Cloud Build, so neither this machine nor the
#                 1 GB VM has to run the Next.js build
#   BUILD=local   build and push with the local Docker instead
#   BUILD=skip    redeploy the tag given in IMAGE_TAG without building
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
# shellcheck source=deploy/gcp/config.sh
source "${HERE}/config.sh"

BUILD="${BUILD:-cloud}"
IMAGE_TAG="${IMAGE_TAG:-$(git -C "${ROOT}" rev-parse --short HEAD)}"
DEMO_EMAIL="${DEMO_EMAIL:-demo@example.com}"
: "${DEMO_PASSWORD:?Set DEMO_PASSWORD: the password of the demo account on the live site}"
SITE_ADDRESS="$(site_address)"

build_image() {
  local service="$1" image="${IMAGE_PREFIX}/$1"
  case "${BUILD}" in
    cloud)
      gcloud builds submit "${ROOT}/${service}" --project "${PROJECT_ID}" \
        --tag "${image}:${IMAGE_TAG}" --quiet
      ;;
    local)
      docker build --platform linux/amd64 -t "${image}:${IMAGE_TAG}" "${ROOT}/${service}"
      docker push "${image}:${IMAGE_TAG}"
      ;;
    skip) ;;
    *)
      echo "BUILD must be cloud, local or skip" >&2
      exit 1
      ;;
  esac
}

remote() {
  gcloud compute ssh "${VM_NAME}" --project "${PROJECT_ID}" --zone "${ZONE}" \
    --tunnel-through-iap --quiet --command "$1"
}

log "Building images with tag ${IMAGE_TAG} (${BUILD})"
if [[ "${BUILD}" == "local" ]]; then
  gcloud auth configure-docker "${REGISTRY_HOST}" --quiet
fi
build_image backend
build_image frontend

log "Uploading the stack definition to ${VM_NAME}"
staging="$(mktemp -d)"
trap 'rm -rf "${staging}"' EXIT
cp "${ROOT}/deploy/docker-compose.prod.yml" "${staging}/docker-compose.yml"
cp "${ROOT}/deploy/Caddyfile" "${HERE}/backup.sh" "${staging}/"
# Single quotes keep Compose from interpolating characters such as $ in the password.
if [[ "${DEMO_PASSWORD}" == *"'"* ]]; then
  echo "DEMO_PASSWORD must not contain a single quote" >&2
  exit 1
fi
cat > "${staging}/.env" <<ENV
SITE_ADDRESS=${SITE_ADDRESS}
IMAGE_PREFIX=${IMAGE_PREFIX}
IMAGE_TAG=${IMAGE_TAG}
DEMO_EMAIL=${DEMO_EMAIL}
DEMO_PASSWORD='${DEMO_PASSWORD}'
DATA_DIR=${REMOTE_DIR}/data
ENV
remote "rm -rf /tmp/route53-deploy"
gcloud compute scp --recurse "${staging}" "${VM_NAME}:/tmp/route53-deploy" \
  --project "${PROJECT_ID}" --zone "${ZONE}" --tunnel-through-iap --quiet

log "Starting the stack"
remote "set -e
  sudo install -m 0644 /tmp/route53-deploy/docker-compose.yml /tmp/route53-deploy/Caddyfile ${REMOTE_DIR}/
  sudo install -m 0600 /tmp/route53-deploy/.env ${REMOTE_DIR}/.env
  sudo install -m 0755 /tmp/route53-deploy/backup.sh ${REMOTE_DIR}/backup.sh
  rm -rf /tmp/route53-deploy
  sudo gcloud auth configure-docker ${REGISTRY_HOST} --quiet
  cd ${REMOTE_DIR}
  sudo docker compose pull --quiet
  sudo docker compose up -d --remove-orphans
  sudo docker image prune -af >/dev/null
  sudo docker compose ps"

log "Smoke test: https://${SITE_ADDRESS}"
for attempt in $(seq 1 30); do
  if curl -fsS "https://${SITE_ADDRESS}/api/v1/health" 2>/dev/null | grep -q '"status":"ok"'; then
    echo "API healthy after ${attempt} attempt(s)."
    status="$(curl -s -o /dev/null -w '%{http_code}' "https://${SITE_ADDRESS}/signin")"
    echo "Sign-in page: HTTP ${status}"
    echo "Live at https://${SITE_ADDRESS}"
    exit 0
  fi
  sleep 10
done
echo "The site did not become healthy. Inspect it with:" >&2
echo "  gcloud compute ssh ${VM_NAME} --zone ${ZONE} --tunnel-through-iap --command 'cd ${REMOTE_DIR} && sudo docker compose logs --tail 100'" >&2
exit 1
