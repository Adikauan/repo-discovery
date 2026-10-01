from datetime import timedelta
from uuid import uuid4
from threading import Lock
import time
from dataclasses import replace

import pytest

from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.application.use_cases.process_mining_execution import ProcessMiningExecution
from app.application.use_cases.process_repository import ProcessRepository
from app.domain.entities.execution_snapshot import ExecutionSnapshotV1, ExecutionSnapshotV2, ExecutionSnapshotV3, ExecutionSnapshotV4, SnapshotMiningTarget, SnapshotGroup
from app.domain.author_policy import AuthorPolicy
from app.domain.entities.mining_execution import MiningExecution
from app.domain.entities.repository_execution import RepositoryExecution
from app.domain.entities.mining_scope import MiningScope, SelectedGitLabGroup, SelectedGitLabRepository
from app.domain.value_objects.repository_context import RepositoryFileMetadata
from app.domain.value_objects.mining_failure import MiningFailure
from app.domain.value_objects.normalized_commit import NormalizedCommit
from app.domain.entities.repository_checkpoint import RepositoryCheckpoint
from tests.fakes import FakeCipher, MemoryUnitOfWork
from tests.unit.test_mining_execution import NOW


class FakeMiningProvider:
    def __init__(self): self.requests = []
    def get_project_scope(self, url, token, project_id):
        self.requests.append(("scope-project", project_id))
        return type("Project", (), {"id": project_id, "name": "sample", "full_path": "team/sample"})()
    def project(self, url, token, project_id):
        self.requests.append(("project", project_id))
        return {"id": project_id, "name": "sample", "full_path": "team/sample", "default_branch": "master"}
    def tree(self, url, token, project_id, branch):
        self.requests.append(("tree", project_id, branch))
        return (RepositoryFileMetadata("src/main.py"), RepositoryFileMetadata("vendor/lib.js"))
    def get_branch_head(self, url, token, project_id, branch): return NormalizedCommit("a" * 40, None)
    def is_commit_reachable(self, *args): return True
    def list_commits_after(self, *args, **kwargs): return ()
    def get_group(self, *_): raise AssertionError("unexpected group lookup")
    def group_children(self, *_): raise AssertionError("unexpected group lookup")


def configured_execution():
    uow = MemoryUnitOfWork()
    config_id = uuid4()
    from app.domain.monitoring_configuration import MonitoringConfiguration
    config = MonitoringConfiguration.create(identifier=config_id, name="historical", gitlab_url="https://gitlab.example.com", now=NOW)
    uow.configuration_repository.add(config)
    fingerprint = normalized_url_fingerprint(config.gitlab_url)
    selection = SelectedGitLabRepository(uuid4(), fingerprint, 12, "sample", "team/sample", None, NOW)
    uow.scopes[config_id] = MiningScope(config_id, 1, NOW, repositories=(selection,))
    encrypted = FakeCipher().encrypt("token")
    uow.credential_repository.replace(config_id, encrypted, None, NOW)
    uow.credential_repository.update_validation(config_id, 1, fingerprint, "success", NOW)
    snapshot = ExecutionSnapshotV4.capture(config, uow.scopes[config_id], mining_targets=[SnapshotMiningTarget(gitlab_project_id=12, instance_fingerprint=fingerprint, name="sample", full_path="team/sample", branch="qualidade")])
    execution = MiningExecution.create(snapshot, NOW)
    running = execution.transition("running", NOW + timedelta(seconds=1), expected_status="pending")
    uow.execution_repository.add(running)
    uow.commit()
    return uow, running


def test_manual_pipeline_persists_real_summary_and_counters():
    uow, execution = configured_execution()
    provider = FakeMiningProvider()
    result = ProcessMiningExecution(uow, provider, FakeCipher(), clock=lambda: NOW + timedelta(seconds=2)).execute(execution.id)
    rows, total = uow.repository_execution_repository.list_for_execution(execution.id)
    assert result.status == "completed"
    assert (result.repository_count, result.successful_repository_count, result.failed_repository_count, result.finding_count) == (1, 1, 0, 0)
    assert total == 1 and rows[0].status == "completed"
    assert rows[0].processed_branch == "qualidade" and rows[0].file_count == 1
    assert ("tree", 12, "qualidade") in provider.requests
    assert not any(call[-1] == "master" for call in provider.requests if len(call) > 2)
    assert rows[0].observed_extensions == (".py",) and rows[0].finding_count == 0
    assert all("token" not in repr(value) for value in uow.repository_execution_repository.items.values())
    assert len(uow.checkpoints) == 1
    assert next(iter(uow.checkpoints.values())).last_successful_commit_hash == "a" * 40


def test_one_repository_with_multiple_policy_branches_gets_independent_baselines_and_checkpoints():
    uow, execution = configured_execution()
    from dataclasses import replace
    from app.domain.entities.execution_snapshot import SnapshotMiningTarget

    fingerprint = normalized_url_fingerprint(execution.snapshot.gitlab_url)
    targets = tuple(SnapshotMiningTarget(gitlab_project_id=12, instance_fingerprint=fingerprint,
        name="sample", full_path="team/sample", branch=branch, allowed_author_emails=())
        for branch in ("main", "dev-larah"))
    uow.executions[execution.id] = replace(execution,
        snapshot=execution.snapshot.model_copy(update={"mining_targets": targets}))

    class BranchRecordingProvider(FakeMiningProvider):
        def __init__(self): super().__init__(); self.processed = []
        def tree(self, url, token, project_id, branch):
            self.processed.append(branch)
            return ()
        def get_branch_head(self, url, token, project_id, branch):
            return NormalizedCommit(("a" if branch == "main" else "b") * 40, None)

    provider = BranchRecordingProvider()
    result = ProcessMiningExecution(uow, provider, FakeCipher(), clock=lambda: NOW + timedelta(seconds=2)).execute(execution.id)
    rows, total = uow.repository_execution_repository.list_for_execution(execution.id)

    assert result.status == "completed" and total == 2
    assert set(provider.processed) == {"main", "dev-larah"}
    assert {item.target_branch for item in rows} == {"main", "dev-larah"}
    assert uow.repository_checkpoint_repository.get(execution.monitoring_configuration_id, 12, "main").last_successful_commit_hash == "a" * 40
    assert uow.repository_checkpoint_repository.get(execution.monitoring_configuration_id, 12, "dev-larah").last_successful_commit_hash == "b" * 40


def test_incremental_processing_persists_findings_and_advances_checkpoint():
    uow, execution = configured_execution()
    first = RepositoryExecution.create(execution.id, 12, "sample", "team/sample", "qualidade")
    uow.repository_execution_repository.add(first); uow.commit()
    ProcessRepository(uow, FakeMiningProvider(), clock=lambda: NOW + timedelta(seconds=2)).execute(first, execution.snapshot, "token")
    old = uow.checkpoints[(execution.monitoring_configuration_id, 12, "qualidade")]
    row = RepositoryExecution.create(uuid4(), 12, "sample", "team/sample", "qualidade")
    uow.repository_execution_repository.add(row); uow.commit()
    class IncrementalProvider(FakeMiningProvider):
        def get_branch_head(self, *args): return NormalizedCommit("b" * 40, None)
        def list_commits_after(self, *args, **kwargs):
            return (NormalizedCommit("c" * 40, "unknown@example.com", "Untrusted"),
                    NormalizedCommit("d" * 40, "unknown@example.com", "Untrusted"))
    result = ProcessRepository(uow, IncrementalProvider(), clock=lambda: NOW + timedelta(seconds=3)).execute(row, execution.snapshot, "token")
    assert result.status == "completed" and result.finding_count == 2
    assert len(uow.findings) == 2
    assert uow.checkpoints[(execution.monitoring_configuration_id, 12, "qualidade")].last_successful_commit_hash == "b" * 40
    assert old.last_successful_commit_hash == "a" * 40


def test_author_policies_apply_only_to_the_branch_already_processed_by_mining():
    uow, execution = configured_execution()
    configuration = replace(uow.configuration_repository.get(execution.monitoring_configuration_id),
                            author_policy_mode="scope_aware")
    fingerprint = normalized_url_fingerprint(configuration.gitlab_url)
    trunk_policy = AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=configuration.id,
        instance_fingerprint=fingerprint, gitlab_project_id=12, branch="qualidade", full_path="team/sample",
        allowed_author_emails=["authorized@example.com"])
    release_policy = AuthorPolicy.repository_branch(identifier=uuid4(), configuration_id=configuration.id,
        instance_fingerprint=fingerprint, gitlab_project_id=12, branch="release", full_path="team/sample",
        allowed_author_emails=["other@example.com"])
    snapshot = ExecutionSnapshotV2.capture(configuration, uow.mining_scope_repository.get(configuration.id),
        policies=[trunk_policy, release_policy])
    uow.repository_checkpoint_repository.put(RepositoryCheckpoint(uuid4(), configuration.id, 12, "qualidade", "a" * 40, NOW))
    row = RepositoryExecution.create(execution.id, 12, "sample", "team/sample", "qualidade")
    uow.repository_execution_repository.add(row); uow.commit()

    class PolicyProvider(FakeMiningProvider):
        def __init__(self): super().__init__(); self.processed_branches = []
        def tree(self, url, token, project_id, branch):
            self.processed_branches.append(branch)
            return super().tree(url, token, project_id, branch)
        def get_branch_head(self, url, token, project_id, branch): return NormalizedCommit("b" * 40, None)
        def list_commits_after(self, *args, **kwargs):
            return (NormalizedCommit("c" * 40, "authorized@example.com"),
                    NormalizedCommit("d" * 40, "unauthorized@example.com"))

    provider = PolicyProvider()
    result = ProcessRepository(uow, provider, clock=lambda: NOW + timedelta(seconds=2)).execute(row, snapshot, "token")
    assert provider.processed_branches == ["qualidade"]
    assert result.processed_branch == "qualidade" and result.finding_count == 1
    finding = next(iter(uow.findings.values()))
    assert finding.author_email == "unauthorized@example.com"
    assert uow.checkpoints[(configuration.id, 12, "qualidade")].last_successful_commit_hash == "b" * 40


def test_execution_finding_counter_reconciles_with_persisted_rows():
    uow, execution = configured_execution()
    uow.repository_checkpoint_repository.put(RepositoryCheckpoint(uuid4(), execution.monitoring_configuration_id,
        12, "qualidade", "a" * 40, NOW))
    class FindingProvider(FakeMiningProvider):
        def get_branch_head(self, *args): return NormalizedCommit("b" * 40, None)
        def list_commits_after(self, *args, **kwargs): return (NormalizedCommit("c" * 40, "unknown@example.com"),)
    result = ProcessMiningExecution(uow, FindingProvider(), FakeCipher(), clock=lambda: NOW + timedelta(seconds=2)).execute(execution.id)
    rows, _ = uow.repository_execution_repository.list_for_execution(execution.id)
    assert result.finding_count == sum(item.finding_count for item in rows) == len(uow.findings) == 1


@pytest.mark.parametrize("failure", ["finding_persistence", "unreachable", "limit"])
def test_incremental_failure_keeps_previous_checkpoint_and_finding_store_unchanged(failure):
    uow, execution = configured_execution()
    uow.checkpoints[(execution.monitoring_configuration_id, 12, "qualidade")] = RepositoryCheckpoint(
        uuid4(), execution.monitoring_configuration_id, 12, "qualidade", "a" * 40, NOW)
    row = RepositoryExecution.create(uuid4(), 12, "sample", "team/sample", "qualidade")
    uow.repository_execution_repository.add(row); uow.commit()
    class IncrementalProvider(FakeMiningProvider):
        def get_branch_head(self, *args): return NormalizedCommit("b" * 40, None)
        def is_commit_reachable(self, *args): return failure != "unreachable"
        def list_commits_after(self, *args, **kwargs):
            if failure == "limit": raise MiningFailure("commit_range_limit_exceeded")
            return (NormalizedCommit("c" * 40, "unauthorized@example.com"),)
    if failure == "finding_persistence":
        def fail_add(_): raise RuntimeError("database private detail")
        uow.finding_repository.add = fail_add
    result = ProcessRepository(uow, IncrementalProvider(), clock=lambda: NOW + timedelta(seconds=3),
        max_commits=1).execute(row, execution.snapshot, "token")
    assert result.status == "failed"
    assert result.error_code == ("repository_checkpoint_unreachable" if failure == "unreachable" else
        "commit_range_limit_exceeded" if failure == "limit" else "repository_processing_failed")
    assert uow.checkpoints[(execution.monitoring_configuration_id, 12, "qualidade")].last_successful_commit_hash == "a" * 40
    assert uow.findings == {}


def test_valid_empty_scope_completes_with_zero_counters():
    uow, execution = configured_execution()
    from dataclasses import replace
    snapshot = execution.snapshot.model_copy(update={"repositories": (), "mining_targets": ()})
    uow.executions[execution.id] = replace(execution, snapshot=snapshot)
    result = ProcessMiningExecution(uow, FakeMiningProvider(), FakeCipher(), clock=lambda: NOW + timedelta(seconds=2)).execute(execution.id)
    assert result.status == "completed"
    assert (result.repository_count, result.successful_repository_count, result.failed_repository_count, result.finding_count) == (0, 0, 0, 0)


def test_interrupted_repository_worker_leaves_persisted_running_row_untouched():
    uow, execution = configured_execution()
    row = RepositoryExecution.create(execution.id, 12, "sample", "team/sample", "qualidade")
    uow.repository_execution_repository.add(row); uow.commit()
    class Interrupted(BaseException): pass
    class InterruptingProvider(FakeMiningProvider):
        def project(self, *_): raise Interrupted()
    with pytest.raises(Interrupted):
        ProcessRepository(uow, InterruptingProvider(), clock=lambda: NOW + timedelta(seconds=2)).execute(row, execution.snapshot, "secret")
    saved = uow.repository_execution_repository.get(row.id)
    parent = uow.execution_repository.get(execution.id)
    assert saved.status == "running" and saved.started_at == NOW + timedelta(seconds=2)
    assert saved.completed_at is None and saved.processed_branch is None and saved.file_count == 0
    assert saved.observed_extensions == () and saved.error_code is None
    assert parent.status == "running" and parent.successful_repository_count == 0


def test_unexpected_provider_exception_is_normalized_without_raw_text():
    uow, execution = configured_execution()
    row = RepositoryExecution.create(execution.id, 12, "sample", "team/sample", "qualidade")
    uow.repository_execution_repository.add(row); uow.commit()
    class UnsafeProvider(FakeMiningProvider):
        def project(self, *_): raise RuntimeError("token=secret database password=private raw response")
    result = ProcessRepository(uow, UnsafeProvider(), clock=lambda: NOW + timedelta(seconds=2)).execute(row, execution.snapshot, "secret")
    assert result.status == "failed" and result.error_code == "repository_processing_failed"
    assert result.error_summary == "Repository processing could not be completed."
    assert "secret" not in repr(result) and "database" not in result.error_summary


@pytest.mark.parametrize("code", ["repository_not_found", "repository_forbidden", "repository_timeout", "repository_invalid_response", "repository_tree_limit_exceeded"])
def test_repository_provider_failure_codes_are_allowlisted_and_safe(code):
    uow, execution = configured_execution()
    row = RepositoryExecution.create(execution.id, 12, "sample", "team/sample", "qualidade")
    uow.repository_execution_repository.add(row); uow.commit()
    class FailingProvider(FakeMiningProvider):
        def project(self, *_): raise MiningFailure(code)
    result = ProcessRepository(uow, FailingProvider(), clock=lambda: NOW + timedelta(seconds=2)).execute(row, execution.snapshot, "hidden-token")
    assert result.status == "failed" and result.error_code == code
    assert result.error_summary and "hidden-token" not in result.error_summary


def test_repository_workers_respect_configured_bound():
    uow, execution = configured_execution()
    from dataclasses import replace
    from app.domain.entities.execution_snapshot import SnapshotRepository
    from app.domain.entities.mining_scope import SelectedGitLabRepository
    fingerprint = normalized_url_fingerprint(execution.snapshot.gitlab_url)
    selections = tuple(SelectedGitLabRepository(uuid4(), fingerprint, project, f"repo-{project}", f"team/repo-{project}", None, NOW) for project in range(20, 26))
    uow.scopes[execution.monitoring_configuration_id] = MiningScope(execution.monitoring_configuration_id, 1, NOW, repositories=selections)
    targets = tuple(SnapshotMiningTarget(gitlab_project_id=item.gitlab_project_id, instance_fingerprint=fingerprint,
        name=item.name, full_path=item.full_path, branch="quality") for item in selections)
    snapshot = execution.snapshot.model_copy(update={"repositories": tuple(SnapshotRepository(gitlab_project_id=item.gitlab_project_id, name=item.name, full_path=item.full_path, instance_fingerprint=fingerprint) for item in selections), "mining_targets": targets})
    uow.executions[execution.id] = replace(execution, snapshot=snapshot)
    class BoundedProvider(FakeMiningProvider):
        def __init__(self): super().__init__(); self.active = 0; self.maximum = 0; self.lock = Lock()
        def project(self, url, token, project_id):
            with self.lock: self.active += 1; self.maximum = max(self.maximum, self.active)
            time.sleep(.01)
            with self.lock: self.active -= 1
            return {"id": project_id, "name": f"repo-{project_id}", "full_path": f"team/repo-{project_id}", "default_branch": "trunk"}
        def tree(self, *args): return ()
    provider = BoundedProvider()
    result = ProcessMiningExecution(uow, provider, FakeCipher(), concurrency=2, worker_uow_factory=lambda: uow,
                                    clock=lambda: NOW + timedelta(seconds=2)).execute(execution.id)
    assert result.status == "completed" and result.repository_count == 6
    assert 1 < provider.maximum <= 2


def test_unavailable_target_branch_fails_only_that_repository_without_default_fallback():
    uow, execution = configured_execution()
    from dataclasses import replace
    from app.domain.entities.execution_snapshot import SnapshotRepository
    fingerprint = normalized_url_fingerprint(execution.snapshot.gitlab_url)
    selections = tuple(SelectedGitLabRepository(uuid4(), fingerprint, project, f"repo-{project}", f"team/repo-{project}", None, NOW) for project in (20, 21))
    targets = tuple(SnapshotMiningTarget(gitlab_project_id=item.gitlab_project_id, instance_fingerprint=fingerprint,
        name=item.name, full_path=item.full_path, branch="quality") for item in selections)
    snapshot = execution.snapshot.model_copy(update={"repositories": tuple(SnapshotRepository(gitlab_project_id=item.gitlab_project_id, name=item.name, full_path=item.full_path, instance_fingerprint=fingerprint) for item in selections), "mining_targets": targets})
    uow.executions[execution.id] = replace(execution, snapshot=snapshot)
    class BranchProvider(FakeMiningProvider):
        def tree(self, url, token, project_id, branch):
            assert branch == "quality"
            if project_id == 20:
                raise MiningFailure("repository_not_found")
            return ()
    result = ProcessMiningExecution(uow, BranchProvider(), FakeCipher(), clock=lambda: NOW + timedelta(seconds=3)).execute(execution.id)
    rows, _ = uow.repository_execution_repository.list_for_execution(execution.id)
    failed = next(item for item in rows if item.gitlab_project_id == 20)
    assert result.status == "partially_completed"
    assert result.repository_count == 2 and result.successful_repository_count == 1 and result.failed_repository_count == 1
    assert failed.status == "failed" and failed.error_code == "repository_target_branch_unavailable"
    assert failed.target_branch == "quality"
    assert all(item.status in {"completed", "failed"} for item in rows)


def test_preprocessing_failure_creates_no_repository_rows_and_provider_details_stay_hidden():
    uow, execution = configured_execution()
    uow.credential_repository.remove(execution.monitoring_configuration_id)
    provider = FakeMiningProvider()
    result = ProcessMiningExecution(uow, provider, FakeCipher(), clock=lambda: NOW + timedelta(seconds=2)).execute(execution.id)
    rows, total = uow.repository_execution_repository.list_for_execution(execution.id)
    assert result.status == "failed" and result.error_code == "gitlab_credential_missing"
    assert total == 0 and rows == [] and provider.requests == []


def test_instance_mismatch_blocks_provider_calls_for_historical_ids():
    uow, execution = configured_execution()
    from dataclasses import replace
    snapshot = execution.snapshot.model_copy(update={"gitlab_url": "https://different.gitlab.example.com"})
    uow.executions[execution.id] = replace(execution, snapshot=snapshot)
    provider = FakeMiningProvider()
    result = ProcessMiningExecution(uow, provider, FakeCipher(), clock=lambda: NOW + timedelta(seconds=2)).execute(execution.id)
    assert result.status == "failed" and result.error_code == "gitlab_instance_mismatch"
    assert provider.requests == []


def test_legacy_v3_snapshot_is_not_resumed_with_obsolete_scope_targets():
    uow, execution = configured_execution()
    config = uow.configuration_repository.get(execution.monitoring_configuration_id)
    from app.domain.entities.execution_snapshot import ExecutionSnapshotV3
    legacy = ExecutionSnapshotV3.capture(config, uow.mining_scope_repository.get(config.id))
    uow.executions[execution.id] = replace(execution, snapshot=legacy)
    class MissingBranch(FakeMiningProvider):
        def project(self, *_): raise AssertionError("legacy snapshot must fail before provider processing")
    result = ProcessMiningExecution(uow, MissingBranch(), FakeCipher(), clock=lambda: NOW + timedelta(seconds=2)).execute(execution.id)
    rows, total = uow.repository_execution_repository.list_for_execution(execution.id)
    assert result.status == "failed" and result.error_code == "orchestration_failed"
    assert total == 0 and rows == []
