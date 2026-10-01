from datetime import UTC, datetime, time
from uuid import uuid4

from sqlalchemy import inspect

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.monitoring_configuration import MonitoringConfiguration


def test_schedule_table_is_migration_managed_and_configuration_can_have_no_schedule(pg_uow_factory):
    uow = pg_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Schedule migration",
        gitlab_url="https://gitlab.example", now=datetime(2026, 1, 1, tzinfo=UTC))
    uow.configuration_repository.add(configuration)
    uow.commit()
    assert "monitoring_schedules" in inspect(uow.session.get_bind()).get_table_names()
    state = uow.schedule_repository.get(configuration.id)
    assert not state.configured and state.version == 0


def test_schedule_persistence_increments_version_and_rejects_stale_cas(pg_uow_factory):
    uow = pg_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Schedule persistence",
        gitlab_url="https://gitlab.example", now=datetime(2026, 1, 1, tzinfo=UTC))
    uow.configuration_repository.add(configuration)
    uow.commit()
    first = MonitoringSchedule.create(configuration_id=configuration.id, recurrence_type="daily", enabled=True,
        execution_time=time(10), timezone="UTC", now=datetime(2026, 1, 1, tzinfo=UTC), version=1)
    assert uow.schedule_repository.replace(first, 0)
    uow.commit()
    stored = uow.schedule_repository.get(configuration.id)
    assert stored.version == 1 and stored.execution_time == time(10)
    second = MonitoringSchedule.create(configuration_id=configuration.id, recurrence_type="weekly", enabled=True,
        execution_time=time(11), timezone="America/Sao_Paulo", day_of_week=1,
        now=datetime(2026, 1, 2, tzinfo=UTC), version=2)
    assert uow.schedule_repository.replace(second, 1)
    uow.commit()
    assert not uow.schedule_repository.replace(first, 1)
    uow.rollback()
    winner = uow.schedule_repository.get(configuration.id)
    assert winner.version == 2 and winner.recurrence_type.value == "weekly"

