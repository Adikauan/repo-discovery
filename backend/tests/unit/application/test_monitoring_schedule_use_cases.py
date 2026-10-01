from datetime import UTC, datetime, time
from uuid import uuid4

import pytest

from app.application.use_cases.replace_monitoring_schedule import ReplaceMonitoringSchedule
from app.domain.errors import FieldValidationError, StaleConfigurationError
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork

NOW = datetime(2026, 9, 28, 12, tzinfo=UTC)


def prepared():
    uow = MemoryUnitOfWork()
    item = MonitoringConfiguration.create(identifier=uuid4(), name="Schedule fixture",
        description="Unrelated description", gitlab_url="https://gitlab.example", now=NOW)
    uow.configuration_repository.add(item)
    return uow, item


def body(**overrides):
    return {"recurrence_type": "daily", "enabled": True, "execution_time": "09:30",
            "timezone": "UTC", "day_of_week": None, "day_of_month": None, **overrides}


def test_valid_schedule_preserves_runtime_supported_timezone_identifier():
    uow, config = prepared()
    saved = ReplaceMonitoringSchedule(uow, lambda: NOW).execute(
        config.id, body(timezone="Etc/UTC"), 0)
    assert saved.schedule.timezone == "Etc/UTC"
    assert uow.schedule_repository.get(config.id).timezone == "Etc/UTC"


@pytest.mark.parametrize("payload", [
    body(execution_time=""), body(execution_time="25:00"),
    body(timezone="Not/A_Real_Zone"), body(recurrence_type="weekly"),
    body(recurrence_type="weekly", day_of_week=0),
    body(recurrence_type="monthly"), body(recurrence_type="monthly", day_of_month=0),
    body(recurrence_type="monthly", day_of_month=32), body(day_of_week=1),
])
def test_invalid_replacement_does_not_replace_existing_schedule(payload):
    uow, config = prepared()
    original = ReplaceMonitoringSchedule(uow, lambda: NOW).execute(config.id, body(), 0).schedule
    with pytest.raises(FieldValidationError):
        ReplaceMonitoringSchedule(uow, lambda: NOW).execute(config.id, payload, original.version)
    assert uow.schedule_repository.get(config.id) == original


def test_stale_schedule_write_is_rejected_and_winner_remains():
    uow, config = prepared()
    winner = ReplaceMonitoringSchedule(uow, lambda: NOW).execute(config.id, body(), 0).schedule
    with pytest.raises(StaleConfigurationError):
        ReplaceMonitoringSchedule(uow, lambda: NOW).execute(config.id, body(execution_time="11:00"), 0)
    assert uow.schedule_repository.get(config.id) == winner
