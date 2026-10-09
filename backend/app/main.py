"""Application factory. Run with ``uvicorn --factory app.main:create_app``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRoute

from app.config import Settings, get_settings
from app.db import create_db_engine, create_session_factory
from app.error_handlers import register_error_handlers
from app.middleware import SameOriginMiddleware
from app.routers import auth, health, hosted_zones, records, transfer
from app.services.throttle import LoginThrottle, SlidingWindowCounter

API_PREFIX = "/api/v1"
DOCS_URL = "/api/docs"

_DESCRIPTION = """
Backend of the Route 53 console clone. Hosted zones and record sets follow Route 53's
rules: every zone owns an apex NS and SOA record, CNAMEs cannot share a name with other
records, and change batches are atomic.

Sign in with `POST /api/v1/auth/login`; the session travels in an httpOnly cookie.
Errors always have the shape `{code, message, details}`.
"""


def _operation_id(route: APIRoute) -> str:
    return route.name


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(
        title="Route 53 Clone API",
        version="1.0.0",
        description=_DESCRIPTION,
        docs_url=DOCS_URL,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        generate_unique_id_function=_operation_id,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.login_throttle = LoginThrottle(
        max_failures=settings.login_max_failures,
        max_failures_per_client=settings.login_max_failures_per_client,
        window=settings.login_failure_window_seconds,
    )
    app.state.sandbox_creations = SlidingWindowCounter(
        settings.sandbox_creations_per_hour, window=3600
    )
    register_error_handlers(app)
    app.add_middleware(SameOriginMiddleware, trusted_origins=settings.trusted_origins)

    api = APIRouter(prefix=API_PREFIX)
    for module in (health, auth, hosted_zones, records, transfer):
        api.include_router(module.router)
    app.include_router(api)

    @app.get("/docs", include_in_schema=False)
    def docs_redirect() -> RedirectResponse:
        return RedirectResponse(DOCS_URL)

    return app
