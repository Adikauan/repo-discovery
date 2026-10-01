from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.errors import ConflictError

SAFE_REPOSITORY_ERRORS = {
    "repository_not_found": "The selected repository is unavailable.",
    "repository_forbidden": "The selected repository cannot be accessed.",
    "repository_timeout": "The repository request timed out.",
    "repository_invalid_response": "GitLab returned an invalid repository response.",
    # Retained so historical records using the pre-017 error remain readable.
    "repository_default_branch_missing": "The repository has no default branch to process.",
    "repository_target_branch_missing": "No target branch is configured for this repository.",
    "repository_target_branch_unavailable": "The configured target branch is unavailable.",
    "target_branch_ambiguous": "Target branches could not be resolved safely for this repository.",
    "repository_tree_limit_exceeded": "The repository tree exceeds the configured processing limit.",
    "repository_processing_failed": "Repository processing could not be completed.",
    "commit_range_limit_exceeded": "The repository commit range exceeds the configured processing limit.",
    "repository_checkpoint_unreachable": "The stored repository checkpoint is no longer reachable from the selected branch.",
    "author_policy_ambiguous": "The configured author policy is ambiguous for this repository.",
}


def _utc(value):
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Aware timestamps are required.")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class RepositoryExecution:
    id: UUID
    mining_execution_id: UUID
    gitlab_project_id: int
    repository_name: str
    repository_full_path: str
    status: str = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    processed_branch: str | None = None
    file_count: int = 0
    observed_extensions: tuple[str, ...] = ()
    extensions_truncated: bool = False
    finding_count: int = 0
    error_code: str | None = None
    error_summary: str | None = None
    target_branch: str | None = None

    def __post_init__(self):
        if type(self.gitlab_project_id) is not int or self.gitlab_project_id <= 0:
            raise ValueError("GitLab project ID must be positive.")
        if not self.repository_name.strip() or not self.repository_full_path.strip():
            raise ValueError("Repository name and path are required.")
        if self.target_branch is not None and (not self.target_branch.strip() or self.target_branch != self.target_branch.strip()):
            raise ValueError("Target branch must be a normalized non-empty branch name.")
        if self.status not in {"pending", "running", "completed", "failed"}:
            raise ValueError("Invalid repository execution status.")
        for field in ("file_count", "finding_count"):
            if type(getattr(self, field)) is not int or getattr(self, field) < 0:
                raise ValueError("Repository counters must be nonnegative integers.")
        if len(self.observed_extensions) > 100 or tuple(sorted(set(self.observed_extensions))) != self.observed_extensions:
            raise ValueError("Observed extensions must be unique, sorted, and bounded.")
        for field in ("started_at", "completed_at"):
            object.__setattr__(self, field, _utc(getattr(self, field)))
        if self.status == "pending" and (self.started_at or self.completed_at):
            raise ValueError("Pending repository timestamps are invalid.")
        if self.status == "running" and (self.started_at is None or self.completed_at is not None):
            raise ValueError("Running repository timestamps are invalid.")
        if self.status in {"completed", "failed"} and (self.started_at is None or self.completed_at is None):
            raise ValueError("Final repository timestamps are required.")
        if self.error_code is not None:
            if self.status != "failed" or SAFE_REPOSITORY_ERRORS.get(self.error_code) != self.error_summary:
                raise ValueError("Repository error metadata must use a safe normalized value.")
        elif self.error_summary is not None:
            raise ValueError("Error summary requires an error code.")

    @classmethod
    def create(cls, execution_id, project_id, name, full_path, target_branch=None):
        return cls(uuid4(), execution_id, project_id, name, full_path, target_branch=target_branch)

    def transition(self, target, now, *, expected_status):
        if self.status != expected_status:
            raise ConflictError("The repository execution state changed.")
        now = _utc(now)
        if (self.status, target) == ("pending", "running"):
            return replace(self, status=target, started_at=now)
        if self.status == "running" and target in {"completed", "failed"}:
            if target == "failed":
                code = expected_status if expected_status in SAFE_REPOSITORY_ERRORS else "repository_processing_failed"
                return replace(self, status=target, completed_at=now, error_code=code,
                               error_summary=SAFE_REPOSITORY_ERRORS[code])
            return replace(self, status=target, completed_at=now)
        raise ConflictError("The repository execution transition is not allowed.")

    def with_summary(self, summary):
        if self.status != "running":
            raise ConflictError("Only running repository work can store a summary.")
        return replace(self, processed_branch=summary.processed_branch, file_count=summary.file_count,
                       observed_extensions=summary.observed_extensions,
                       extensions_truncated=summary.extensions_truncated, finding_count=summary.finding_count)

    def fail(self, code, now):
        if self.status != "running" or code not in SAFE_REPOSITORY_ERRORS:
            raise ConflictError("The repository execution cannot be failed in its current state.")
        return replace(self, status="failed", completed_at=_utc(now), error_code=code,
                       error_summary=SAFE_REPOSITORY_ERRORS[code])
