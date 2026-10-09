#!/usr/bin/env bash
# Measure where the time of a request goes: connection setup, sign-in and ordinary API calls.
#
#   ./deploy/measure-latency.sh https://35-208-96-233.sslip.io
#   SAMPLES=20 EMAIL=demo@example.com PASSWORD='...' ./deploy/measure-latency.sh http://localhost:3000
#
# Every figure is the median of SAMPLES requests, in milliseconds.
#   connect   DNS + TCP + TLS for a new connection (zero when the connection is reused)
#   request   from the connection being ready to the last byte of the answer: one network
#             round trip plus the server's work
#   total     connect + request
# "new" rows open a connection per request, as `curl` does. "reused" rows send every
# request over one connection, as a browser does after its first request, so their
# figure is what a page actually experiences.
#
# To separate the network from the server, run the same script on the server itself with
# RESOLVE set, which sends the requests to that address under the site's host name:
#
#   RESOLVE=127.0.0.1 ./measure-latency.sh https://35-208-96-233.sslip.io
#
# There the round trip is zero, so "request" is the server's own time. /api/v1/health
# does almost no work, so from anywhere else its figure is close to one network round trip.
#
# The script signs in SAMPLES * 2 + 1 times; it keeps its cookies, so all of them land in
# one sandbox.
set -euo pipefail

BASE="${1:?usage: measure-latency.sh <base url>}"
BASE="${BASE%/}"
SAMPLES="${SAMPLES:-10}"
EMAIL="${EMAIL:-demo@example.com}"
PASSWORD="${PASSWORD:-Route53Demo!}"

CURL=(curl -s)
if [[ -n "${RESOLVE:-}" ]]; then
  host="${BASE#*://}"
  host="${host%%/*}"
  port=443
  [[ "${BASE}" == http://* ]] && port=80
  [[ "${host}" == *:* ]] && port="${host##*:}" && host="${host%%:*}"
  CURL+=(--resolve "${host}:${port}:${RESOLVE}")
fi

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT
jar="${work}/cookies"
FORMAT='%{time_namelookup} %{time_connect} %{time_appconnect} %{time_pretransfer} %{time_starttransfer} %{time_total} %{http_code} %{num_connects}\n'
LOGIN_BODY="$(printf '{"email":"%s","password":"%s"}' "${EMAIL}" "${PASSWORD}")"

median() {
  sort -n | awk '{ v[NR] = $1 } END { if (NR == 0) { print "-"; exit } m = (NR % 2) ? v[(NR + 1) / 2] : (v[NR / 2] + v[NR / 2 + 1]) / 2; printf "%.0f", m * 1000 }'
}

# report <label> <file of FORMAT lines>
report() {
  local label="$1" file="$2" codes
  codes="$(awk '{ print $7 }' "${file}" | sort -u | tr '\n' ' ')"
  printf '%-34s %8s %8s %8s   HTTP %s\n' "${label}" \
    "$(awk '{ print $4 }' "${file}" | median)" \
    "$(awk '{ print $6 - $4 }' "${file}" | median)" \
    "$(awk '{ print $6 }' "${file}" | median)" \
    "${codes}"
}

# new_connections <label> <curl args...>: one connection per request.
new_connections() {
  local label="$1" out="${work}/new"
  shift
  : > "${out}"
  for _ in $(seq "${SAMPLES}"); do
    "${CURL[@]}" -o /dev/null -w "${FORMAT}" "$@" >> "${out}"
  done
  report "${label} (new)" "${out}"
}

# reused_connection <label> <url> [curl args...]: SAMPLES requests over one connection;
# the first one, which pays for the connection, is dropped.
reused_connection() {
  local label="$1" url="$2" out="${work}/reused" urls=()
  shift 2
  for _ in $(seq $((SAMPLES + 1))); do urls+=(-o /dev/null "${url}"); done
  "${CURL[@]}" -w "${FORMAT}" "$@" "${urls[@]}" | tail -n "+2" > "${out}"
  report "${label} (reused)" "${out}"
}

echo "Target: ${BASE}${RESOLVE:+ at ${RESOLVE}}   samples: ${SAMPLES}"
printf '%-34s %8s %8s %8s\n' "" "connect" "request" "total"

new_connections "GET  /api/v1/health" "${BASE}/api/v1/health"
reused_connection "GET  /api/v1/health" "${BASE}/api/v1/health"

# Sign in once and keep the cookies: the session for the authenticated requests, and the
# sandbox so the sign-ins measured below reuse it instead of each creating a new one.
"${CURL[@]}" -o /dev/null -c "${jar}" -X POST -H 'Content-Type: application/json' \
  -d "${LOGIN_BODY}" "${BASE}/api/v1/auth/login"

new_connections "POST /api/v1/auth/login" -b "${jar}" -X POST \
  -H 'Content-Type: application/json' -d "${LOGIN_BODY}" "${BASE}/api/v1/auth/login"
reused_connection "POST /api/v1/auth/login" "${BASE}/api/v1/auth/login" -b "${jar}" -X POST \
  -H 'Content-Type: application/json' -d "${LOGIN_BODY}"
new_connections "GET  /api/v1/auth/me" -b "${jar}" "${BASE}/api/v1/auth/me"
reused_connection "GET  /api/v1/auth/me" "${BASE}/api/v1/auth/me" -b "${jar}"
new_connections "GET  /api/v1/hostedzones" -b "${jar}" "${BASE}/api/v1/hostedzones?page_size=100"
reused_connection "GET  /api/v1/hostedzones" "${BASE}/api/v1/hostedzones?page_size=100" -b "${jar}"
reused_connection "GET  /route53/v2/hostedzones" "${BASE}/route53/v2/hostedzones" -b "${jar}"
new_connections "GET  /signin" "${BASE}/signin"
