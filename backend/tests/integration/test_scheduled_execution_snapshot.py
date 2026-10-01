from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

from app.application.use_cases.create_mining_execution import CreateMiningExecution
from app.application.use_cases.replace_monitoring_schedule import ReplaceMonitoringSchedule
from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.monitoring_configuration import MonitoringConfiguration

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def test_occurrence_and_schedule_version_are_persisted_immutably_after_schedule_edit(pg_uow_factory):
    uow = pg_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Scheduled snapshot",
        gitlab_url="https://gitlab.example", now=NOW)
    configuration = replace(configuration, enabled=True)
    uow.configuration_repository.add(configuration)
    schedule = MonitoringSchedule.create(configuration_id=configuration.id, recurrence_type="daily",
        enabled=True, execution_time=time(10), timezone="UTC", now=NOW-timedelta(days=2), version=1)
    uow.schedule_repository.replace(schedule, 0)
    uow.commit()

    occurrence = NOW-timedelta(minutes=1)
    created = CreateMiningExecution(uow, clock=lambda: NOW).execute(configuration.id,
        trigger_type="scheduled", scheduled_occurrence=occurrence,
        expected_schedule_version=schedule.version).execution
    assert created.trigger_type == "scheduled"
    before = pg_uow_factory().execution_repository.get(created.id)
    assert before.scheduled_occurrence_at == occurrence
    assert before.snapshot.schedule_context.scheduled_occurrence == occurrence
    assert before.snapshot.schedule_context.schedule_version == 1

    edited = ReplaceMonitoringSchedule(pg_uow_factory(), now=lambda: NOW).execute(configuration.id, {
        "recurrence_type": "weekly", "enabled": True, "execution_time": time(11), "timezone": "UTC",
        "day_of_week": 4, "day_of_month": None,
    }, expected_version=1)
    assert edited.schedule.version == 2
    after = pg_uow_factory().execution_repository.get(created.id)
    assert after.snapshot == before.snapshot
    assert after.scheduled_occurrence_at == before.scheduled_occurrence_at
