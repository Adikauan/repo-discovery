import math
import pytest
from pydantic import ValidationError

from app.config import Settings


def settings(**values):
    values.setdefault("scheduler_enabled", True)
    return Settings(database_url="postgresql://unused", cors_origins="http://localhost", **values)


def test_gitlab_timeout_defaults_are_positive_and_finite():
    value = settings()
    assert (value.gitlab_connect_timeout_seconds, value.gitlab_read_timeout_seconds,
            value.gitlab_write_timeout_seconds, value.gitlab_pool_timeout_seconds) == (5, 10, 5, 5)
    assert all(math.isfinite(item) and item > 0 for item in (
        value.gitlab_connect_timeout_seconds, value.gitlab_read_timeout_seconds,
        value.gitlab_write_timeout_seconds, value.gitlab_pool_timeout_seconds))


@pytest.mark.parametrize("invalid", [0, -1, float("nan"), float("inf"), float("-inf")])
def test_invalid_timeout_is_rejected_without_exposing_other_settings(invalid):
    with pytest.raises(ValidationError) as caught:
        settings(gitlab_connect_timeout_seconds=invalid, gitlab_credential_encryption_keys="secret-key")
    assert "secret-key" not in str(caught.value)


def test_repository_mining_setting_defaults():
    value = settings()
    assert value.repository_mining_concurrency == 4
    assert value.repository_mining_max_tree_entries == 50_000
    assert value.repository_mining_max_file_bytes == 1_048_576
    assert value.repository_mining_max_extensions == 100
    assert value.mining_max_commits_per_repository_execution == 1000


def test_commit_limit_setting_accepts_configured_value():
    assert settings(mining_max_commits_per_repository_execution=250).mining_max_commits_per_repository_execution == 250


@pytest.mark.parametrize("invalid", [0, 10001])
def test_commit_limit_setting_rejects_out_of_range(invalid):
    with pytest.raises(ValidationError):
        settings(mining_max_commits_per_repository_execution=invalid)


def test_scheduler_setting_defaults():
    value = settings()
    assert value.scheduler_enabled is True
    assert value.schedule_poll_interval_seconds == 10
    assert value.scheduled_execution_concurrency == 4


@pytest.mark.parametrize(("field", "valid"), [
    ("schedule_poll_interval_seconds", 1), ("schedule_poll_interval_seconds", 60),
    ("scheduled_execution_concurrency", 1), ("scheduled_execution_concurrency", 8),
])
def test_scheduler_setting_bounds(field, valid):
    assert getattr(settings(**{field: valid}), field) == valid


@pytest.mark.parametrize(("field", "invalid"), [
    ("schedule_poll_interval_seconds", 0), ("schedule_poll_interval_seconds", 61),
    ("scheduled_execution_concurrency", 0), ("scheduled_execution_concurrency", 9),
])
def test_invalid_scheduler_setting_bounds_are_rejected(field, invalid):
    with pytest.raises(ValidationError):
        settings(**{field: invalid})


def test_scheduler_enabled_reads_environment(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    value = Settings(_env_file=None, database_url="postgresql://unused", cors_origins="http://localhost")
    assert value.scheduler_enabled is False


def test_finding_diff_limits_have_approved_defaults():
    value = settings()
    assert value.finding_diff_max_files == 100
    assert value.finding_diff_max_file_bytes == 262144
    assert value.finding_diff_max_total_bytes == 2097152
    assert value.finding_diff_max_path_bytes == 4096


@pytest.mark.parametrize(("field", "value"), [
    ("finding_diff_max_files", 10), ("finding_diff_max_file_bytes", 1024),
    ("finding_diff_max_total_bytes", 4096), ("finding_diff_max_path_bytes", 256),
])
def test_finding_diff_limits_accept_configured_values(field, value):
    assert getattr(settings(**{field: value}), field) == value


@pytest.mark.parametrize(("field", "value"), [
    ("finding_diff_max_files", 0), ("finding_diff_max_files", 101),
    ("finding_diff_max_file_bytes", 0), ("finding_diff_max_file_bytes", 262145),
    ("finding_diff_max_total_bytes", 0), ("finding_diff_max_total_bytes", 2097153),
    ("finding_diff_max_path_bytes", 0), ("finding_diff_max_path_bytes", 4097),
])
def test_finding_diff_limits_reject_out_of_range_values(field, value):
    with pytest.raises(ValidationError):
        settings(**{field: value})


@pytest.mark.parametrize(("field", "invalid"), [
    ("repository_mining_concurrency", 0), ("repository_mining_concurrency", 9),
    ("repository_mining_max_tree_entries", 0), ("repository_mining_max_file_bytes", -1),
    ("repository_mining_max_extensions", 0), ("repository_mining_max_extensions", 101),
])
def test_invalid_repository_mining_bounds_are_rejected(field, invalid):
    with pytest.raises(ValidationError):
        settings(**{field: invalid})
