import asyncio
import json

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.api.errors import domain_error_handler, request_validation_error_handler
from app.domain.errors import (BadRequestError, ConflictError, CredentialServiceUnavailable,
                               FieldValidationError, MissingPreconditionError, NotFoundError,
                               StaleConfigurationError)


def request():
    return Request({"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                    "method": "GET", "scheme": "http", "path": "/", "raw_path": b"/",
                    "query_string": b"", "headers": [], "server": ("test", 80), "client": ("test", 1)})


@pytest.mark.parametrize(("error", "status", "code"), [
    (BadRequestError("invalid request"), 400, "invalid_request"),
    (NotFoundError("not found"), 404, "not_found"),
    (ConflictError("conflict"), 409, "conflict"),
    (StaleConfigurationError("stale"), 412, "stale_update"),
    (FieldValidationError("timezone", "invalid_timezone", "Choose a timezone."), 422, "validation_error"),
    (MissingPreconditionError("missing precondition"), 428, "invalid_precondition"),
    (CredentialServiceUnavailable(), 503, "unexpected_error"),
    (RuntimeError("INTERNAL_SENTINEL database password stack trace"), 500, "unexpected_error"),
])
def test_global_handler_has_deterministic_safe_problem_code(error, status, code):
    response = asyncio.run(domain_error_handler(request(), error))
    body = json.loads(response.body)
    assert response.status_code == status
    assert body["code"] == code
    assert body["status"] == status
    if status == 500:
        assert "INTERNAL_SENTINEL" not in response.body.decode()
        assert "database password" not in response.body.decode()
        assert "stack trace" not in response.body.decode()
        assert body["detail"] == "The request could not be completed."


def test_request_validation_problem_details_has_validation_error_code():
    error = RequestValidationError([{"type": "missing", "loc": ("body", "executionTime"),
                                     "msg": "Field required", "input": None}])
    response = asyncio.run(request_validation_error_handler(request(), error))
    body = json.loads(response.body)
    assert response.status_code == 422
    assert body["code"] == "validation_error"
    assert body["errors"][0]["field"] == "executionTime"
