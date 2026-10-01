from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from threading import Event
from uuid import uuid4

import pytest

from app.application.scheduling.scheduled_execution_dispatcher import ScheduledExecutionDispatcher, ScheduledOccurrenceCandidate
from app.application.use_cases.create_manual_execution import CreateManualExecution
from app.application.use_cases.process_mining_execution import ProcessMiningExecution
from app.application.use_cases.transition_execution import TransitionExecution
from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.errors import ConflictError
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import FakeCipher

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def seed_schedule(factory):
    uow = factory()
    config = MonitoringConfiguration.create(identifier=uuid4(), name="Scheduled race",
        gitlab_url="https://gitlab.example", now=NOW)
    config = replace(config, enabled=True)
    uow.configuration_repository.add(config)
    schedule = MonitoringSchedule.create(configuration_id=config.id, recurrence_type="daily", enabled=True,
        execution_time=time(10), timezone="UTC", now=NOW-timedelta(days=1), version=1)
    uow.schedule_repository.replace(schedule, 0)
    uow.commit()
    return config, schedule


class FinishingPipeline:
    def __init__(self, uow): self.uow = uow
    def execute(self, identifier):
        return TransitionExecution(self.uow, lambda: NOW).execute(identifier, "running", "completed")


def test_duplicate_occurrence_after_terminal_execution_is_idempotent(pg_uow_factory):
    config, schedule = seed_schedule(pg_uow_factory)
    occurrence = NOW-timedelta(minutes=1)
    def pipeline_factory(uow): return FinishingPipeline(uow)
    dispatcher = ScheduledExecutionDispatcher(pg_uow_factory, pipeline_factory, clock=lambda: NOW)
    candidate = ScheduledOccurrenceCandidate(config.id, occurrence, schedule.version)
    first = dispatcher.dispatch(candidate)
    replay = dispatcher.dispatch(candidate)
    assert first.outcome == "started" and first.execution.status == "completed"
    assert replay.outcome == "duplicate"
    executions, count = pg_uow_factory().execution_repository.page(page=1, page_size=10, configuration_id=config.id)
    assert count == 1 and executions[0].scheduled_occurrence_at == occurrence


@pytest.mark.parametrize("winner_trigger", ["manual", "scheduled"])
def test_only_one_manual_or_scheduled_request_enters_pipeline(pg_uow_factory, winner_trigger):
    config, schedule = seed_schedule(pg_uow_factory)
    occurrence = NOW-timedelta(minutes=1)
    first_uow = pg_uow_factory()
    locked, release_lock, entered, release_pipeline = Event(), Event(), Event(), Event()
    original_lock = first_uow.configuration_repository.lock_active

    def pause_after_lock(identifier):
        configuration = original_lock(identifier)
        locked.set()
        assert release_lock.wait(10)
        return configuration

    first_uow.configuration_repository.lock_active = pause_after_lock

    class BlockingPipeline:
        def __init__(self, uow): self.uow = uow
        def execute(self, identifier):
            entered.set()
            assert release_pipeline.wait(10)
            return TransitionExecution(self.uow, lambda: NOW).execute(identifier, "running", "completed")

    def scheduled(uow):
        dispatcher = ScheduledExecutionDispatcher(lambda: uow, lambda current: BlockingPipeline(current), clock=lambda: NOW)
        return dispatcher.dispatch(ScheduledOccurrenceCandidate(config.id, occurrence, schedule.version))

    def manual(uow):
        return CreateManualExecution(uow, clock=lambda: NOW,
            mining_pipeline=BlockingPipeline(uow)).execute(config.id)

    # Execute the winning request on another thread so its config row lock can be observed.
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(scheduled if winner_trigger == "scheduled" else manual, first_uow)
        assert locked.wait(10)
        losing_uow = pg_uow_factory()
        try:
            if winner_trigger == "scheduled":
                with pytest.raises(ConflictError):
                    manual(losing_uow)
            else:
                losing_result = scheduled(losing_uow)
                assert losing_result.outcome == "conflict"
        finally:
            release_lock.set()
        assert entered.wait(10)
        release_pipeline.set()
        result = future.result(10)

    execution_id = result.execution.id if winner_trigger == "scheduled" else result.id
    check = pg_uow_factory()
    executions, total = check.execution_repository.page(page=1, page_size=10, configuration_id=config.id)
    assert total == 1 and executions[0].id == execution_id and executions[0].status == "completed"
    assert entered.is_set()


def test_scheduled_pipeline_is_feature_008_process_mining_execution(pg_uow_factory):
    from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
    config, schedule = seed_schedule(pg_uow_factory)
    cipher = FakeCipher()
    uow = pg_uow_factory()
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    uow.credential_repository.replace(config.id, cipher.encrypt("token"), None, NOW)
    uow.credential_repository.update_validation(config.id, 1, fingerprint, "success", NOW)
    uow.commit()

    class EmptyProvider: pass
    dispatcher = ScheduledExecutionDispatcher(pg_uow_factory,
        lambda current: ProcessMiningExecution(current, EmptyProvider(), cipher, clock=lambda: NOW), clock=lambda: NOW)
    result = dispatcher.dispatch(ScheduledOccurrenceCandidate(config.id, NOW-timedelta(minutes=1), schedule.version))
    assert result.execution.status == "completed"
    assert result.execution.repository_mining_completed is True
    assert result.execution.finding_count == 0
