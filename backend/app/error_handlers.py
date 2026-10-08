"""Translate every failure into the common ``{code, message, details}`` body."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import AppError

logger = logging.getLogger(__name__)

_LOCATION_PREFIXES = frozenset({"body", "query", "path", "cookie", "header"})
_STATUS_CODES = {404: "NotFound", 405: "MethodNotAllowed"}


def _body(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details or []}


async def _handle_app_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status_code)


async def _handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part not in _LOCATION_PREFIXES)
            or None,
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        _body("ValidationError", "The request is not valid.", details), status_code=422
    )


async def _handle_http_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _STATUS_CODES.get(exc.status_code, "HttpError")
    return JSONResponse(
        _body(code, str(exc.detail)), status_code=exc.status_code, headers=exc.headers
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        _body("InternalFailure", "The request failed because of an internal error."),
        status_code=500,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
