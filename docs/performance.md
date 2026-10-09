# Response times: what was measured and what changed

The live site runs on one e2-micro VM in `us-central1`. From India, API calls measured
with `curl` took 0.9 to 2.2 seconds. This page records where that time goes, what was
changed, and how to repeat the measurements. Figures are medians in milliseconds,
taken on 9 October 2026.

## Where the time goes

`deploy/measure-latency.sh` times the same requests twice: with a new connection for each
(what `curl` does) and over one reused connection (what a browser does after its first
request). Run on the VM itself with `RESOLVE=127.0.0.1`, it takes the network out and
leaves the server's own time.

| Request | From India, new connection | From India, reused connection | On the server |
|---|---|---|---|
| `GET /api/v1/health` | 983 (631 connecting) | 324 | 6 |
| `POST /api/v1/auth/login` | 1214 (657 connecting) | 552 | 188 |
| `GET /api/v1/auth/me` | 956 (661 connecting) | 380 | 7 |
| `GET /api/v1/hostedzones` | 1101 (766 connecting) | 336 | 11 |
| `GET /route53/v2/hostedzones` (page) | | 303 | 9 |

What this shows:

- **The server is not slow.** Ordinary API calls take 6 to 11 ms of server time. The VM was
  idle while it served them (load average 0.14, each container at under 1% CPU and about
  80 MB of memory), so a larger machine would not help.
- **A network round trip to `us-central1` costs about 300 ms from India**, and opening a
  new TLS connection costs about 650 ms more. A one-off `curl` pays both, which is the
  "0.9 seconds per API call". A browser pays for the connection once.
- **Sign-in is the one request with real server time: 188 ms, all of it Argon2.** Timed
  inside the backend container, verifying one password with the library's default
  parameters took 188 ms.

So the experience is governed by how many round trips a page makes one after another,
plus Argon2 at sign-in.

## What changed

### Password hashing parameters

Timed inside the backend container on the VM, one verification each:

| Argon2id parameters | Time |
|---|---|
| 64 MiB, 3 passes, 4 lanes (argon2-cffi default, RFC 9106 low-memory profile) | 188 ms |
| 46 MiB, 1 pass, 1 lane (OWASP option) | 86 ms |
| **19 MiB, 2 passes, 1 lane (OWASP option)** | **38 ms** |
| 12 MiB, 3 passes, 1 lane (OWASP option) | 33 ms |

The backend now uses 19 MiB, 2 passes, 1 lane. This is one of the configurations the
OWASP Password Storage Cheat Sheet lists as equivalent in strength for Argon2id; it is
weaker than the previous setting against an attacker with a lot of memory per guess, and
it is still a memory-hard, salted hash. The trade-off is acceptable here because the only
account's password is printed on the sign-in page, and because 64 MiB per sign-in is a
fifth of the free memory of a 1 GB machine. Hashes made with the old parameters are
verified as they are and replaced with a new hash at the next successful sign-in. No
password is stored or compared in plain text, and verification is never skipped.

### Fewer round trips in a row

A browser trace of the live site showed the pages waiting on requests one after another:

- The sign-in page loaded its scripts, and only then asked the API for the credentials it
  displays. The page now arrives with them, so that request no longer exists.
- After sign-in, the browser fetched the console's scripts (37 files), and only then asked
  for the list of zones. The sign-in page now downloads the console's scripts while the
  visitor is reading it, and the zone list is requested the moment sign-in succeeds.
- Opening a zone fetched that page's scripts, then the zone, then its records. The list
  page now downloads the zone page's scripts when idle, and following a zone's link
  requests the zone and its records at once.

Measured with Chromium on a production build, with 300 ms of latency and a 10 Mbit/s link
emulated through the DevTools protocol (median of three cold runs):

| From click to content | Before | After |
|---|---|---|
| Open the sign-in page, until the credentials are shown | 2253 | 1660 |
| Sign in, until the zones are listed | 3357 | 1414 |
| Open a zone, until its records are listed | 1453 | 925 |

These are measurements of an emulated link, not of the live site. The emulation adds its
latency to every request but does not model connection setup, so the first page load of a
real visit is slower than the first row suggests.

## What was not changed

- **The region.** Moving the VM to Mumbai (`asia-south1`) would take about 250 ms off every
  round trip for visitors in India. It was not done: the free tier covers an e2-micro only
  in `us-west1`, `us-central1` and `us-east1`, so by my estimate from the list prices it
  would cost $7 to $8 a month more, and it would change the site's address.
- **The machine size.** The measurements above show no CPU or memory pressure.

## Repeating the measurements

```bash
# From anywhere: connection setup, sign-in and API calls, new and reused connections
./deploy/measure-latency.sh https://35-208-96-233.sslip.io

# On the server: the same requests without the network
gcloud compute scp deploy/measure-latency.sh route53-clone:/tmp/ --zone us-central1-a --tunnel-through-iap
gcloud compute ssh route53-clone --zone us-central1-a --tunnel-through-iap \
  --command 'RESOLVE=127.0.0.1 bash /tmp/measure-latency.sh https://35-208-96-233.sslip.io'
```

`SAMPLES`, `EMAIL` and `PASSWORD` can be set in the environment; the script's header
explains its columns.
