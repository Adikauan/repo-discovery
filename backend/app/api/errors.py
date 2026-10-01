from fastapi import Request
from fastapi.responses import JSONResponse

from fastapi.exceptions import RequestValidationError

from app.domain.errors import (BadRequestError, ConflictError, FieldValidationError,
                               CredentialReplacementConflict, CredentialServiceUnavailable,
                               GitLabDiscoveryError, MissingPreconditionError, NotFoundError,
                               StaleConfigurationError, CommitDiffError)
from app.domain.errors import AuthorPolicyApiError


def _safe_code(status: int) -> str:
    return {
        400: "invalid_request", 404: "not_found", 409: "conflict", 412: "stale_update",
        422: "validation_error", 428: "invalid_precondition", 500: "unexpected_error",
        502: "unexpected_error", 503: "unexpected_error", 504: "unexpected_error",
    }.get(status, "unexpected_error")


async def domain_error_handler(request: Request, error: Exception):
    if isinstance(error, CommitDiffError):
        status, title, detail, errors = error.status, "Commit diff unavailable", error.detail, None
        code = error.code
    elif isinstance(error, AuthorPolicyApiError):
        status, title, detail, errors, code = error.status, "Author policy request failed", error.detail, None, error.code
    elif isinstance(error, FieldValidationError):
        status, title, detail = 422, "Validation failed", error.message
        errors = [{"field": error.field, "code": error.code, "message": error.message}]
    elif isinstance(error, BadRequestError):
        status, title, detail, errors = 400, "Bad request", str(error), None
    elif isinstance(error, NotFoundError):
        status, title, detail, errors = 404, "Not found", str(error), None
    elif isinstance(error, MissingPreconditionError):
        status, title, detail, errors = 428, "Precondition required", str(error), None
    elif isinstance(error, StaleConfigurationError):
        status, title, detail, errors = 412, "Precondition failed", str(error), None
    elif isinstance(error, ConflictError):
        status, title, detail, errors = 409, "Conflict", str(error), None
    elif isinstance(error, CredentialServiceUnavailable):
        status, title, detail, errors = 503, "Service unavailable", "Credential service is unavailable.", None
    elif isinstance(error, GitLabDiscoveryError):
        if error.outcome == "timeout":
            status, title, detail = 504, "Gateway timeout", "GitLab did not respond in time. Try again."
        elif error.outcome in {"rate_limited", "provider_unavailable"}:
            status, title, detail = 503, "Service unavailable", "GitLab is temporarily unavailable. Try again."
        else:
            status, title, detail = 502, "Bad gateway", "GitLab could not complete the requested operation."
        errors = None
    else:
        status, title, detail, errors = 500, "Internal server error", "The request could not be completed.", None
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail,
            "code": code if isinstance(error, (CommitDiffError, AuthorPolicyApiError)) else _safe_code(status)}
    if errors is not None: body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


async def request_validation_error_handler(request: Request, error: RequestValidationError):
    details = []
    for item in error.errors():
        location = item.get("loc", ())
        field = str(location[-1]) if location else "request"
        details.append({"field": field, "code": str(item.get("type", "invalid")),
                        "message": "Review this value and try again."})
    return JSONResponse({"type": "about:blank", "title": "Validation failed", "status": 422,
                         "code": "validation_error",
                         "detail": "Review the fields and try again.", "errors": details},
                        status_code=422, media_type="application/problem+json")
