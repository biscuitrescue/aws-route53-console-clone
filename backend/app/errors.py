"""Application errors. Every error reaches the client as ``{code, message, details}``."""

from typing import Any

ErrorDetail = dict[str, Any]


class AppError(Exception):
    status_code = 400
    code = "BadRequest"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        field: str | None = None,
        details: list[ErrorDetail] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.headers = headers
        if code is not None:
            self.code = code
        self.field = field
        if details is None:
            details = [{"field": field, "message": message}] if field else []
        self.details = details


class InvalidInputError(AppError):
    status_code = 400
    code = "InvalidInput"


class InvalidDomainNameError(AppError):
    status_code = 400
    code = "InvalidDomainName"


class InvalidChangeBatchError(AppError):
    status_code = 400
    code = "InvalidChangeBatch"


class InvalidZoneFileError(AppError):
    status_code = 400
    code = "InvalidZoneFile"


class LimitExceededError(AppError):
    """A quota of the account or of one hosted zone would be exceeded."""

    status_code = 400
    code = "LimitsExceeded"


class UnauthorizedError(AppError):
    status_code = 401
    code = "Unauthorized"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "Throttling"

    def __init__(self, message: str, *, retry_after: float) -> None:
        # Rounded up, so a client that waits this long is certain to be let through.
        seconds = max(1, int(-(-retry_after // 1)))
        super().__init__(message, headers={"Retry-After": str(seconds)})


class NotFoundError(AppError):
    status_code = 404
    code = "NotFound"


class ConflictError(AppError):
    status_code = 409
    code = "Conflict"
