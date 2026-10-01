from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4

import pytest

from app.application.use_cases.create_mining_execution import CreateMiningExecution
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.author_policy import AuthorPolicy
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from app.domain.entities.mining_execution import MiningExecution
from app.domain.entities.monitoring_schedule import MonitoringSchedule
from app.domain.errors import ConflictError, FieldValidationError
from app.domain.monitoring_configuration import MonitoringConfiguration
from tests.fakes import MemoryUnitOfWork

NOW = datetime(2026, 9, 30, 12, tzinfo=UTC)


def prepared(*, enabled=True):
    uow = MemoryUnitOfWork()
    configuration = MonitoringConfiguration.create(identifier=uuid4(), name="scheduled fixture",
        gitlab_url="https://gitlab.example", now=NOW)
    configuration = replace(configuration, enabled=enabled)
    uow.configuration_repository.add(configuration)
    schedule = MonitoringSchedule.create(configuration_id=configuration.id, recurrence_type="daily",
        enabled=True, execution_time=time(10), timezone="UTC", now=NOW - timedelta(days=1), version=4)
    uow.schedule_repository.replace(schedule, 0)
    uow.commit()
    return uow, configuration, schedule


class RecordingPipeline:
    def __init__(self):
        self.execution_ids = []

    def execute(self, execution_id):
        self.execution_ids.append(execution_id)


def test_scheduled_creation_captures_internal_context_and_calls_shared_pipeline_once():
    uow, config, schedule = prepared()
    pipeline = RecordingPipeline()
    occurrence = NOW - timedelta(minutes=1)
    result = CreateMiningExecution(uow, clock=lambda: NOW, mining_pipeline=pipeline).execute(
        config.id, trigger_type="scheduled", scheduled_occurrence=occurrence,
        expected_schedule_version=schedule.version)
    assert result.outcome == "started"
    execution = result.execution
    assert execution.trigger_type == "scheduled"
    assert execution.snapshot.trigger_type == "scheduled"
    assert execution.snapshot.schedule_context.scheduled_occurrence == occurrence
    assert execution.snapshot.schedule_context.schedule_version == schedule.version
    assert execution.scheduled_occurrence_at == occurrence
    assert pipeline.execution_ids == [execution.id]


def test_scheduled_execution_captures_the_same_scope_aware_author_policy_context():
    uow, config, schedule = prepared()
    config = replace(config, author_policy_mode="scope_aware")
    uow.configurations[config.id] = config
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    selected = SelectedGitLabRepository(uuid4(), fingerprint, 42, "API", "team/api", None, NOW)
    uow.scopes[config.id] = MiningScope(config.id, 1, NOW, repositories=(selected,))
    policy = AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=config.id,
        instance_fingerprint=fingerprint, gitlab_project_id=42, branch="main", full_path="team/api",
        allowed_author_emails=[" Alice@example.com "])
    uow.author_policy_repository.upsert(policy)
    uow.commit()
    pipeline = RecordingPipeline()
    result = CreateMiningExecution(uow, clock=lambda: NOW, mining_pipeline=pipeline).execute(
        config.id, trigger_type="scheduled", scheduled_occurrence=NOW - timedelta(minutes=1),
        expected_schedule_version=schedule.version)
    assert result.execution.snapshot.schema_version == 2
    assert result.execution.snapshot.author_policy_mode == "scope_aware"
    assert result.execution.snapshot.repository_branch_author_policies[0].branch == "main"
    assert result.execution.snapshot.repository_branch_author_policies[0].allowed_author_emails == ("alice@example.com",)
    assert "credential" not in repr(result.execution.snapshot).casefold()


def test_manual_and_scheduled_triggers_capture_identical_policy_mining_targets():
    from app.domain.entities.execution_snapshot import ExecutionSnapshotV4, SnapshotMiningTarget
    from tests.fakes import FakeCipher

    class Provider:
        def get_project_scope(self, url, token, project_id):
            return type("Project", (), {"id": project_id, "name": "API", "full_path": "team/api"})()
        def get_group(self, *args): raise AssertionError("no selected groups")
        def group_children(self, *args): raise AssertionError("no selected groups")

    snapshots = []
    for trigger in ("manual", "scheduled"):
        uow, config, schedule = prepared()
        fingerprint = normalized_url_fingerprint(config.gitlab_url)
        selected = SelectedGitLabRepository(uuid4(), fingerprint, 42, "API", "team/api", None, NOW)
        uow.scopes[config.id] = MiningScope(config.id, 1, NOW, repositories=(selected,))
        policy = AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=config.id,
            instance_fingerprint=fingerprint, gitlab_project_id=42, branch="dev-larah", full_path="team/api",
            allowed_author_emails=["dev@example.com"])
        uow.author_policy_repository.upsert(policy)
        cipher = FakeCipher()
        encrypted = cipher.encrypt("test-token")
        uow.credential_repository.replace(config.id, encrypted, None, NOW)
        uow.credential_repository.update_validation(config.id, 1, fingerprint, "success", NOW)
        uow.commit()
        pipeline = RecordingPipeline()
        pipeline.provider = Provider()
        pipeline.cipher = cipher
        service = CreateMiningExecution(uow, clock=lambda: NOW, mining_pipeline=pipeline)
        if trigger == "manual":
            result = service.execute(config.id)
        else:
            result = service.execute(config.id, trigger_type="scheduled",
                scheduled_occurrence=NOW - timedelta(minutes=1), expected_schedule_version=schedule.version)
        snapshots.append(result.execution.snapshot)
    assert all(isinstance(snapshot, ExecutionSnapshotV4) for snapshot in snapshots)
    assert [[(target.gitlab_project_id, target.branch) for target in snapshot.mining_targets]
            for snapshot in snapshots] == [[(42, "dev-larah")], [(42, "dev-larah")]]

@pytest.mark.parametrize("mutation", ["disabled_configuration", "disabled_schedule", "removed_schedule",
    "changed_version", "not_due", "at_update_time"])
def test_ineligible_scheduled_candidates_do_not_create_or_invoke_pipeline(mutation):
    uow, config, schedule = prepared()
    occurrence = NOW - timedelta(minutes=1)
    expected_version = schedule.version
    if mutation == "disabled_configuration":
        uow.configurations[config.id] = replace(config, enabled=False)
    elif mutation == "disabled_schedule":
        schedule = replace(schedule, enabled=False)
        uow.schedules[config.id] = schedule
    elif mutation == "removed_schedule":
        uow.schedules[config.id] = MonitoringSchedule.unconfigured(config.id,
            schedule.version + 1, NOW)
    elif mutation == "changed_version":
        expected_version += 1
    elif mutation == "not_due":
        occurrence = NOW + timedelta(seconds=1)
    elif mutation == "at_update_time":
        occurrence = schedule.updated_at
    pipeline = RecordingPipeline()
    result = CreateMiningExecution(uow, clock=lambda: NOW, mining_pipeline=pipeline).execute(
        config.id, trigger_type="scheduled", scheduled_occurrence=occurrence,
        expected_schedule_version=expected_version)
    assert result.outcome == "ineligible"
    assert not uow.executions and not pipeline.execution_ids


def test_scheduled_candidate_losing_active_guard_is_skipped_without_pipeline():
    uow, config, schedule = prepared()
    active = MiningExecution.create(
        __import__("app.domain.entities.execution_snapshot", fromlist=["ExecutionSnapshotV1"]).ExecutionSnapshotV1.capture(
            config, uow.mining_scope_repository.get(config.id)), NOW - timedelta(seconds=1))
    active = active.transition("running", NOW - timedelta(seconds=1), expected_status="pending")
    uow.execution_repository.add(active)
    uow.commit()
    pipeline = RecordingPipeline()
    result = CreateMiningExecution(uow, clock=lambda: NOW, mining_pipeline=pipeline).execute(
        config.id, trigger_type="scheduled", scheduled_occurrence=NOW - timedelta(minutes=1),
        expected_schedule_version=schedule.version)
    assert result.outcome == "conflict" and result.execution is None
    assert uow.execution_repository.active_for(config.id) == active
    assert not pipeline.execution_ids


def test_duplicate_scheduled_occurrence_does_not_reenter_pipeline():
    uow, config, schedule = prepared()
    pipeline = RecordingPipeline()
    service = CreateMiningExecution(uow, clock=lambda: NOW, mining_pipeline=pipeline)
    arguments = dict(trigger_type="scheduled", scheduled_occurrence=NOW - timedelta(minutes=1),
        expected_schedule_version=schedule.version)
    first = service.execute(config.id, **arguments)
    uow.execution_repository.transition(first.execution.transition(
        "failed", NOW, expected_status="running", error_code="orchestration_failed"), "running")
    uow.commit()
    replay = service.execute(config.id, **arguments)
    assert first.outcome == "started" and replay.outcome == "duplicate"
    assert len(uow.executions) == 1 and len(pipeline.execution_ids) == 1


def test_manual_execution_is_rejected_before_persisting_when_group_descendant_lacks_policy():
    from tests.fakes import FakeCipher

    class Provider:
        def get_project_scope(self, url, token, project_id):
            return type("Project", (), {"id": project_id, "name": f"repo-{project_id}", "full_path": f"team/repo-{project_id}"})()
        def get_group(self, *args): return object()
        def group_children(self, *args):
            return (), (type("Project", (), {"id": 42, "name": "repo-42", "full_path": "team/repo-42"})(),
                        type("Project", (), {"id": 43, "name": "repo-43", "full_path": "team/repo-43"})())

    uow, config, _ = prepared()
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    group = SelectedGitLabGroup(uuid4(), fingerprint, 31, "Team", "team", None, NOW)
    uow.scopes[config.id] = MiningScope(config.id, 1, NOW, groups=(group,))
    policy = AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=config.id,
        instance_fingerprint=fingerprint, gitlab_project_id=42, branch="dev-larah", full_path="team/repo-42",
        allowed_author_emails=["dev@example.com"])
    uow.author_policy_repository.upsert(policy)
    cipher = FakeCipher()
    uow.credential_repository.replace(config.id, cipher.encrypt("token"), None, NOW)
    uow.credential_repository.update_validation(config.id, 1, fingerprint, "success", NOW)
    uow.commit()
    pipeline = RecordingPipeline(); pipeline.provider = Provider(); pipeline.cipher = cipher
    with pytest.raises(FieldValidationError) as error:
        CreateMiningExecution(uow, clock=lambda: NOW, mining_pipeline=pipeline).execute(config.id)
    assert error.value.field == "policies" and error.value.code == "incomplete"
    assert not uow.executions
