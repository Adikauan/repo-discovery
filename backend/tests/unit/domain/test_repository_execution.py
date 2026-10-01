from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.repository_execution import RepositoryExecution
from app.domain.errors import ConflictError


def test_repository_lifecycle_and_safe_failure():
    now = datetime.now(UTC)
    item = RepositoryExecution.create(uuid4(), 7, "repo", "team/repo")
    running = item.transition("running", now, expected_status="pending")
    failed = running.fail("repository_default_branch_missing", now + timedelta(seconds=1))
    assert failed.status == "failed" and failed.error_summary == "The repository has no default branch to process."
    with pytest.raises(ConflictError):
        failed.transition("completed", now + timedelta(seconds=2), expected_status="failed")
    with pytest.raises(ConflictError):
        RepositoryExecution.create(uuid4(), 7, "repo", "team/repo").fail("repository_processing_failed", now)
