"""Request checks that apply to every route."""

from collections.abc import Iterable
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class SameOriginMiddleware:
    """Refuse state-changing requests that a browser sent on behalf of another site.

    The session cookie is ``SameSite=Lax``, which keeps it off requests from other
    *sites*. It does not help against another origin of the same site, and the demo's
    host name is a subdomain of a shared domain that is not on the public suffix list, so
    its neighbours count as the same site. This check closes that gap without a token:

    * Browsers label every request with ``Sec-Fetch-Site``. Only ``same-origin`` (the
      app's own pages) and ``none`` (typed or bookmarked) may change state.
    * Older browsers send ``Origin`` on such requests instead; it has to name the host
      the request was addressed to.
    * A request with neither header did not come from a browser page, so there is no
      user whose cookie is being borrowed; scripts and tests keep working.
    """

    def __init__(self, app: ASGIApp, trusted_origins: Iterable[str] = ()) -> None:
        self.app = app
        self.trusted_origins = frozenset(origin.rstrip("/").lower() for origin in trusted_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        if self._allowed(Headers(scope=scope)):
            await self.app(scope, receive, send)
            return
        response = JSONResponse(
            {
                "code": "CrossOriginRequest",
                "message": "This request came from another site and was not accepted.",
                "details": [],
            },
            status_code=403,
        )
        await response(scope, receive, send)

    def _allowed(self, headers: Headers) -> bool:
        origin = headers.get("origin", "").rstrip("/").lower()
        if origin and origin in self.trusted_origins:
            return True
        fetch_site = headers.get("sec-fetch-site")
        if fetch_site is not None:
            return fetch_site.lower() in ("same-origin", "none")
        if not origin:
            return True
        # Behind the Next.js proxy the original host arrives as X-Forwarded-Host.
        hosts = {headers.get("host", "").lower()}
        hosts.update(
            host.strip().lower() for host in headers.get("x-forwarded-host", "").split(",")
        )
        hosts.discard("")
        return urlsplit(origin).netloc in hosts
