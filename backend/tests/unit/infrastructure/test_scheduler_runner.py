import asyncio
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from threading import Event
from uuid import uuid4

from app.application.use_cases.create_mining_execution import ExecutionCreationResult
from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.infrastructure.scheduling.scheduler_runner import SchedulerRunner
from tests.fakes import MemoryUnitOfWork

START = datetime(2026, 9, 30, 12, tzinfo=UTC)


def scheduled_uow(*, execution_time=time(10), configuration_id=None):
    uow = MemoryUnitOfWork()
    config = MonitoringConfiguration.create(identifier=configuration_id or uuid4(), name="runner fixture",
        gitlab_url="https://gitlab.example", now=START)
    config = replace(config, enabled=True)
    uow.configuration_repository.add(config)
    schedule = MonitoringSchedule.create(configuration_id=config.id, recurrence_type="daily", enabled=True,
        execution_time=execution_time, timezone="UTC", now=START-timedelta(days=1), version=2)
    uow.schedule_repository.replace(schedule, 0)
    return uow, config, schedule


class RecordingDispatcher:
    def __init__(self):
        self.candidates = []

    def dispatch(self, candidate):
        self.candidates.append(candidate)
        return ExecutionCreationResult("conflict")


def test_runner_reloads_persisted_schedule_and_evaluates_due_occurrence():
    uow, config, _ = scheduled_uow()
    dispatcher = RecordingDispatcher()
    runner = SchedulerRunner(lambda: uow, dispatcher, clock=lambda: START)
    runner._watermark = START

    async def exercise():
        await runner.scan_once(tick_instant=START+timedelta(hours=22))
        await asyncio.gather(*tuple(runner._workers))

    asyncio.run(exercise())
    assert len(dispatcher.candidates) == 1
    assert dispatcher.candidates[0].monitoring_configuration_id == config.id
    assert dispatcher.candidates[0].scheduled_occurrence == datetime(2026, 10, 1, 10, tzinfo=UTC)
    assert runner.watermark == START+timedelta(hours=22)


def test_startup_baseline_skips_offline_missed_occurrence_then_runs_next_due():
    uow, _, _ = scheduled_uow()
    dispatcher = RecordingDispatcher()
    runner = SchedulerRunner(lambda: uow, dispatcher, clock=lambda: START)
    runner._watermark = START

    async def exercise():
        await runner.scan_once(tick_instant=datetime(2026, 10, 1, 9, tzinfo=UTC))
        assert not dispatcher.candidates
        await runner.scan_once(tick_instant=datetime(2026, 10, 1, 10, 1, tzinfo=UTC))
        await asyncio.gather(*tuple(runner._workers))

    asyncio.run(exercise())
    assert len(dispatcher.candidates) == 1
    assert dispatcher.candidates[0].scheduled_occurrence == datetime(2026, 10, 1, 10, tzinfo=UTC)


def test_capacity_skips_due_candidate_without_queueing():
    uow = MemoryUnitOfWork()
    configs = [scheduled_uow()[1] for _ in range(2)]
    for config in configs:
        uow.configuration_repository.add(config)
        # Install distinct due schedules into the shared persisted fake repository.
        schedule = MonitoringSchedule.create(configuration_id=config.id, recurrence_type="daily", enabled=True,
            execution_time=time(10), timezone="UTC", now=START-timedelta(days=1), version=1)
        uow.schedule_repository.replace(schedule, 0)
    entered, release = Event(), Event()

    class BlockingDispatcher:
        def __init__(self): self.started = []
        def dispatch(self, candidate):
            self.started.append(candidate)
            entered.set()
            release.wait(3)
            return ExecutionCreationResult("conflict")

    dispatcher = BlockingDispatcher()
    runner = SchedulerRunner(lambda: uow, dispatcher, concurrency=1, clock=lambda: START)
    runner._watermark = START

    async def exercise():
        await runner.scan_once(tick_instant=START+timedelta(days=1))
        await asyncio.sleep(0.05)
        assert entered.is_set()
        assert runner.active_worker_count == 1
        assert len(dispatcher.started) == 1
        release.set()
        await asyncio.gather(*tuple(runner._workers))

    try:
        asyncio.run(exercise())
    finally:
        release.set()
    assert len(dispatcher.started) == 1


def test_scans_are_serialized_even_if_requested_concurrently():
    uow, _, _ = scheduled_uow()
    dispatcher = RecordingDispatcher()
    runner = SchedulerRunner(lambda: uow, dispatcher, clock=lambda: START)
    runner._watermark = START

    async def exercise():
        await asyncio.gather(
            runner.scan_once(tick_instant=START+timedelta(hours=21)),
            runner.scan_once(tick_instant=START+timedelta(hours=22)),
        )
        await asyncio.gather(*tuple(runner._workers))

    asyncio.run(exercise())
    # First scan admits the occurrence; the second uses the advanced watermark.
    assert len(dispatcher.candidates) == 1


def test_invalid_capacity_settings_are_rejected():
    for concurrency in (0, 9):
        try:
            SchedulerRunner(lambda: MemoryUnitOfWork(), RecordingDispatcher(), concurrency=concurrency)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid scheduler concurrency was accepted")


def test_runner_logs_only_safe_schedule_identifiers_and_outcome(caplog, monkeypatch):
    import logging
    from app.infrastructure.scheduling import scheduler_runner as scheduler_module

    monkeypatch.setattr(scheduler_module.logger, "disabled", False)
    monkeypatch.setattr(scheduler_module.logger, "propagate", True)
    monkeypatch.setattr(scheduler_module.logger, "level", logging.NOTSET)
    uow, config, _ = scheduled_uow()
    runner = SchedulerRunner(lambda: uow, RecordingDispatcher(), clock=lambda: START)
    runner._watermark = START
    worker_callback_completed = None
    original_worker_done = runner._worker_done

    def observe_worker_done(task, candidate):
        original_worker_done(task, candidate)
        worker_callback_completed.set()

    async def exercise():
        nonlocal worker_callback_completed
        worker_callback_completed = asyncio.Event()
        runner._worker_done = observe_worker_done
        await runner.scan_once(tick_instant=START + timedelta(hours=22))
        await asyncio.gather(*tuple(runner._workers))
        # The done callback runs on this loop after worker completion and emits
        # the log record asserted below.
        await asyncio.wait_for(worker_callback_completed.wait(), timeout=1)

    with caplog.at_level(logging.INFO):
        asyncio.run(exercise())

    records = [(record.name, record.levelname, record.message) for record in caplog.records]
    dispatch_record = next((record for record in caplog.records if record.message == "Scheduled occurrence evaluated"), None)
    assert dispatch_record is not None, f"Scheduler callback ran but its safe log was not captured: {records}"
    assert dispatch_record.configuration_id == str(config.id)
    assert dispatch_record.outcome == "conflict"
    assert "token" not in caplog.text.lower()
    assert "provider response" not in caplog.text.lower()
