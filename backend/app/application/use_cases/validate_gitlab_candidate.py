from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from app.domain.monitoring_configuration import normalize_gitlab_url
from app.domain.ports.gitlab_connection_client import GitLabConnectionClient


SAFE_MESSAGES = {
    "success": "GitLab connection validated.",
    "invalid_credentials": "GitLab rejected the credential.",
    "forbidden": "The credential cannot access the validation endpoint.",
    "unreachable": "The GitLab instance could not be reached.",
    "timeout": "The GitLab validation request timed out.",
    "invalid_response": "GitLab returned an unexpected response.",
    "rate_limited": "GitLab rate-limited the validation request.",
    "provider_unavailable": "GitLab is temporarily unavailable.",
}


@dataclass(frozen=True, slots=True)
class CandidateValidation:
    state: str
    result: str
    message: str
    checked_at: datetime


class ValidateGitLabCandidate:
    """Validate transient GitLab connection values without configuration persistence."""

    def __init__(self, client: GitLabConnectionClient,
                 clock: Callable[[], datetime] | None = None):
        self.client = client
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(self, gitlab_url: str, token: str) -> CandidateValidation:
        url = normalize_gitlab_url(gitlab_url)
        result = self.client.validate(url, token)
        outcome = result.outcome
        if outcome == "invalid_url":
            from app.domain.errors import FieldValidationError
            raise FieldValidationError("gitlab_url", "invalid_url", "Enter an absolute HTTP or HTTPS URL.")
        # Never propagate provider-controlled message text on a request that carries a secret.
        message = SAFE_MESSAGES.get(outcome, "GitLab could not complete connection validation.")
        return CandidateValidation(
            state="validated" if result.succeeded else "failed",
            result=outcome,
            message=message,
            checked_at=self.clock(),
        )
