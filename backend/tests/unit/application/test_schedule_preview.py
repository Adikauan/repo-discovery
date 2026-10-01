from datetime import UTC, datetime
from uuid import uuid4

from app.application.use_cases.preview_monitoring_schedule import PreviewMonitoringSchedule
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork


def test_preview_uses_fixed_reference_without_repository_mutation():
    reference = datetime(2026, 4, 1, tzinfo=UTC)
    uow = MemoryUnitOfWork()
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Preview",
        gitlab_url="https://gitlab.example", now=reference)
    uow.configuration_repository.add(config)
    result = PreviewMonitoringSchedule(uow, lambda: reference).execute(config.id, {
        "schedule": {"recurrence_type": "monthly", "enabled": True, "execution_time": "08:00",
                     "timezone": "UTC", "day_of_month": 31},
        "reference_instant": reference,
    })
    assert result == datetime(2026, 4, 30, 8, tzinfo=UTC)
    assert config.id not in uow.schedules
