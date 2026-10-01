from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time
from threading import Barrier
from uuid import uuid4

from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.monitoring_configuration import MonitoringConfiguration


def test_two_concurrent_replacements_have_exactly_one_cas_winner(pg_uow_factory):
    setup = pg_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Concurrent schedule",
        gitlab_url="https://gitlab.example", now=datetime(2026, 1, 1, tzinfo=UTC))
    setup.configuration_repository.add(configuration)
    setup.commit()
    barrier = Barrier(2)

    def attempt(hour):
        uow = pg_uow_factory()
        barrier.wait(timeout=10)
        candidate = MonitoringSchedule.create(configuration_id=configuration.id, recurrence_type="daily",
            enabled=True, execution_time=time(hour), timezone="UTC", now=datetime(2026, 1, 2, tzinfo=UTC))
        won = uow.schedule_repository.replace(candidate, 0)
        if won:
            uow.commit()
        else:
            uow.rollback()
        uow.session.close()
        return won, hour

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, (8, 11)))
    assert sum(won for won, _ in outcomes) == 1
    winning_hour = next(hour for won, hour in outcomes if won)
    reader = pg_uow_factory()
    persisted = reader.schedule_repository.get(configuration.id)
    assert persisted.version == 1 and persisted.execution_time == time(winning_hour)


def test_stale_writer_and_remove_recreate_tombstone_never_restore_old_state(pg_uow_factory):
    uow = pg_uow_factory()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="Schedule tombstone",
        gitlab_url="https://gitlab.example", now=datetime(2026, 1, 1, tzinfo=UTC))
    uow.configuration_repository.add(configuration)
    uow.commit()
    original = MonitoringSchedule.create(configuration_id=configuration.id, recurrence_type="daily", enabled=True,
        execution_time=time(8), timezone="UTC", now=datetime(2026, 1, 1, tzinfo=UTC), version=1)
    assert uow.schedule_repository.replace(original, 0)
    uow.commit()
    tombstone = MonitoringSchedule.unconfigured(configuration.id, 2, datetime(2026, 1, 2, tzinfo=UTC))
    assert uow.schedule_repository.replace(tombstone, 1)
    uow.commit()
    latest = MonitoringSchedule.create(configuration_id=configuration.id, recurrence_type="weekly", enabled=True,
        execution_time=time(10), timezone="UTC", day_of_week=2,
        now=datetime(2026, 1, 3, tzinfo=UTC), version=3)
    assert uow.schedule_repository.replace(latest, 2)
    uow.commit()
    assert not uow.schedule_repository.replace(original, 1)
    uow.rollback()
    current = uow.schedule_repository.get(configuration.id)
    assert current.version == 3 and current.recurrence_type.value == "weekly"
