from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

import pytest

from app.application.scheduling.scheduled_execution_dispatcher import (
    ScheduledExecutionDispatcher, ScheduledOccurrenceCandidate,
)
from app.application.use_cases.process_mining_execution import ProcessMiningExecution
from app.application.use_cases.transition_execution import TransitionExecution
from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup
from app.domain.services.schedule_calculator import calculate_next_occurrence
from app.domain.monitoring_configuration import MonitoringConfiguration
from app.domain.ports.gitlab_credential_repository import CredentialSnapshot
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from tests.fakes import FakeCipher, MemoryUnitOfWork

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def prepared(*, recurrence="daily", enabled=True, timezone="UTC", execution_time=time(10),
             day_of_week=None, day_of_month=None, schedule_updated_at=None):
    uow = MemoryUnitOfWork()
    config = MonitoringConfiguration.create(identifier=uuid4(), name="scheduled",
        gitlab_url="https://gitlab.example", now=NOW)
    config = replace(config, enabled=True)
    uow.configuration_repository.add(config)
    schedule = MonitoringSchedule.create(configuration_id=config.id, recurrence_type=recurrence,
        enabled=enabled, execution_time=execution_time, timezone=timezone, now=schedule_updated_at or NOW-timedelta(days=1),
        day_of_week=day_of_week, day_of_month=day_of_month, version=3)
    uow.schedule_repository.replace(schedule, 0)
    return uow, config, schedule


class CompletingPipeline:
    def __init__(self, uow, status="completed"):
        self.uow, self.status, self.calls = uow, status, []

    def execute(self, identifier):
        self.calls.append(identifier)
        TransitionExecution(self.uow, lambda: NOW).execute(identifier, "running", self.status,
            error_code="orchestration_failed" if self.status == "failed" else None)


@pytest.mark.parametrize("recurrence,kwargs", [
    ("daily", {}), ("weekly", {"day_of_week": 3}), ("monthly", {"day_of_month": 30}),
    ("monthly", {"day_of_month": 31}),
])
def test_dispatch_uses_feature_005_next_occurrence_calculation(recurrence, kwargs):
    uow, config, schedule = prepared(recurrence=recurrence, **kwargs)
    reference = NOW - timedelta(days=1)
    occurrence = calculate_next_occurrence(schedule, reference)
    schedule = replace(schedule, updated_at=reference)
    uow.schedules[config.id] = schedule
    pipeline = CompletingPipeline(uow)
    dispatcher = ScheduledExecutionDispatcher(lambda: uow, lambda current: pipeline,
        clock=lambda: occurrence + timedelta(seconds=1))
    result = dispatcher.dispatch(ScheduledOccurrenceCandidate(config.id, occurrence, schedule.version))
    assert result.outcome == "started"
    assert result.execution.trigger_type == "scheduled"
    assert result.execution.snapshot.schedule_context.schedule_version == schedule.version
    assert pipeline.calls == [result.execution.id]


def test_dispatch_uses_timezone_and_dst_resolutions_from_schedule_calculator():
    cases = [
        ("America/New_York", time(2, 30), datetime(2026, 3, 8, 7, 30, tzinfo=UTC)),
        ("America/New_York", time(1, 30), datetime(2026, 11, 1, 5, 30, tzinfo=UTC)),
    ]
    for zone, local_time, expected in cases:
        uow, config, schedule = prepared(timezone=zone, execution_time=local_time)
        # Feature 005 remains the authority for the DST gap/fold instant.
        reference = (datetime(2026, 3, 7, 12, tzinfo=UTC) if local_time.hour == 2
                     else datetime(2026, 10, 31, 12, tzinfo=UTC))
        due = calculate_next_occurrence(schedule, reference)
        assert due == expected
        schedule = replace(schedule, updated_at=due - timedelta(days=1))
        uow.schedules[config.id] = schedule
        pipeline = CompletingPipeline(uow)
        result = ScheduledExecutionDispatcher(lambda: uow, lambda _: pipeline, clock=lambda: due+timedelta(seconds=1)).dispatch(
            ScheduledOccurrenceCandidate(config.id, due, schedule.version))
        assert result.outcome == "started"


@pytest.mark.parametrize("final_status", ["completed", "partially_completed", "failed"])
def test_scheduled_execution_preserves_shared_pipeline_final_outcome(final_status):
    uow, config, schedule = prepared()
    due = NOW - timedelta(minutes=1)
    uow.schedules[config.id] = replace(schedule, updated_at=due-timedelta(seconds=1))
    pipeline = CompletingPipeline(uow, final_status)
    result = ScheduledExecutionDispatcher(lambda: uow, lambda _: pipeline, clock=lambda: NOW).dispatch(
        ScheduledOccurrenceCandidate(config.id, due, schedule.version))
    assert result.execution.status == final_status
    assert result.execution.trigger_type == "scheduled"
    assert pipeline.calls == [result.execution.id]


class EmptyMiningProvider:
    pass


def test_scheduled_dispatch_invokes_real_feature_008_pipeline():
    uow, config, schedule = prepared()
    cipher = FakeCipher()
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    uow.credentials[config.id] = CredentialSnapshot(config.id, cipher.encrypt("runtime-token"), 1,
        "success", NOW, NOW, fingerprint)
    due = NOW - timedelta(minutes=1)
    uow.schedules[config.id] = replace(schedule, updated_at=due-timedelta(seconds=1))
    pipeline = ProcessMiningExecution(uow, EmptyMiningProvider(), cipher, clock=lambda: NOW)
    result = ScheduledExecutionDispatcher(lambda: uow, lambda _: pipeline, clock=lambda: NOW).dispatch(
        ScheduledOccurrenceCandidate(config.id, due, schedule.version))
    assert result.execution.status == "completed"
    assert result.execution.repository_mining_completed is True
    assert result.execution.finding_count == 0


def test_scheduled_dispatch_skips_execution_when_dynamic_group_has_unconfigured_repository():
    uow, config, schedule = prepared()
    cipher = FakeCipher()
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    uow.credentials[config.id] = CredentialSnapshot(config.id, cipher.encrypt("runtime-token"), 1,
        "success", NOW, NOW, fingerprint)
    uow.scopes[config.id] = MiningScope(config.id, 1, NOW, groups=(SelectedGitLabGroup(
        uuid4(), fingerprint, 31, "Backend", "backend", None, NOW),))

    class DynamicGroupProvider:
        def get_group(self, *args): return object()
        def group_children(self, *args):
            return (), (type("Project", (), {"id": 42, "name": "API", "full_path": "backend/api"})(),)

    due = NOW - timedelta(minutes=1)
    uow.schedules[config.id] = replace(schedule, updated_at=due-timedelta(seconds=1))
    pipeline = ProcessMiningExecution(uow, DynamicGroupProvider(), cipher, clock=lambda: NOW)
    result = ScheduledExecutionDispatcher(lambda: uow, lambda _: pipeline, clock=lambda: NOW).dispatch(
        ScheduledOccurrenceCandidate(config.id, due, schedule.version))

    assert result.outcome == "ineligible"
    assert result.execution is None
    assert uow.executions == {}
