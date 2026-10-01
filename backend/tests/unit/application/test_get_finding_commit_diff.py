from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.application.use_cases.get_finding_commit_diff import GetFindingCommitDiff
from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.domain.errors import CommitDiffError
from app.domain.value_objects.commit_diff import CommitDiffFile, CommitDiffProviderResult


class Repo:
    def __init__(self, value): self.value = value
    def get(self, _): return self.value


def context(rule="unauthorized-commit-author", commit_hash="a" * 40, credential=True):
    now = datetime(2026, 9, 30, tzinfo=UTC); config_id = uuid4(); execution_id = uuid4(); repo_id = uuid4(); finding_id = uuid4()
    url = "https://gitlab.example.com/"
    finding = SimpleNamespace(id=finding_id, repository_execution_id=repo_id, rule_id=rule,
        commit_hash=commit_hash, author_name="Writer", author_email="writer@example.com",
        authored_at=now, commit_message_summary="Change",)
    repository = SimpleNamespace(id=repo_id, mining_execution_id=execution_id, gitlab_project_id=42,
        repository_name="repo", repository_full_path="group/repo")
    execution = SimpleNamespace(id=execution_id, monitoring_configuration_id=config_id,
        snapshot=SimpleNamespace(gitlab_url=url))
    fingerprint = normalized_url_fingerprint(url)
    config = SimpleNamespace(gitlab_url=url)
    cred = SimpleNamespace(last_validation_result="success", validated_url_fingerprint=fingerprint, encrypted_token="cipher") if credential else None
    uow = SimpleNamespace(finding_repository=Repo(finding), repository_execution_repository=Repo(repository),
        execution_repository=Repo(execution), configuration_repository=Repo(config), credential_repository=Repo(cred))
    class Provider:
        def get_commit_diff(self, *args, **kwargs):
            self.args, self.kwargs = args, kwargs
            return CommitDiffProviderResult((CommitDiffFile("a", "a", "modified", "+x", True),), "complete")
    provider = Provider()
    settings = SimpleNamespace(finding_diff_max_files=100, finding_diff_max_file_bytes=100,
        finding_diff_max_total_bytes=200, finding_diff_max_path_bytes=4096)
    return finding, uow, provider, settings


def test_lookup_uses_only_finding_commit_and_owned_repository_project():
    finding, uow, provider, settings = context()
    result = GetFindingCommitDiff(uow, provider, SimpleNamespace(decrypt=lambda _: "server-token"), settings).execute(finding.id)
    assert provider.args == ("https://gitlab.example.com/", "server-token", 42, "a" * 40)
    assert result.finding_id == finding.id and result.files[0].diff == "+x"
    assert result.files_completeness == "complete" and result.total_diff_bytes == 2


def test_missing_credential_fails_before_provider_access():
    finding, uow, provider, settings = context(credential=False)
    with pytest.raises(CommitDiffError) as error:
        GetFindingCommitDiff(uow, provider, object(), settings).execute(finding.id)
    assert error.value.code == "gitlab_credential_missing"
    assert not hasattr(provider, "args")


def test_instance_mismatch_fails_before_credential_or_provider_lookup():
    finding, uow, provider, settings = context()
    configuration = uow.configuration_repository.value
    uow.configuration_repository.value = SimpleNamespace(gitlab_url="https://different.example.net")
    with pytest.raises(CommitDiffError) as error:
        GetFindingCommitDiff(uow, provider, object(), settings).execute(finding.id)
    assert error.value.code == "gitlab_instance_mismatch"
    assert not hasattr(provider, "args")


def test_unsupported_finding_does_not_query_provider():
    finding, uow, provider, settings = context(rule="other-rule")
    with pytest.raises(CommitDiffError) as error:
        GetFindingCommitDiff(uow, provider, object(), settings).execute(finding.id)
    assert error.value.code == "finding_diff_not_applicable"
    assert not hasattr(provider, "args")


def test_missing_commit_hash_is_not_applicable_and_does_not_query_provider():
    finding, uow, provider, settings = context()
    finding.commit_hash = None
    with pytest.raises(CommitDiffError) as error:
        GetFindingCommitDiff(uow, provider, object(), settings).execute(finding.id)
    assert error.value.code == "finding_diff_not_applicable"
    assert not hasattr(provider, "args")


def test_provider_failure_does_not_mutate_or_remove_the_historical_finding():
    finding, uow, provider, settings = context()
    provider.get_commit_diff = lambda *args, **kwargs: (_ for _ in ()).throw(CommitDiffError("commit_diff_unavailable"))
    with pytest.raises(CommitDiffError):
        GetFindingCommitDiff(uow, provider, SimpleNamespace(decrypt=lambda _: "token"), settings).execute(finding.id)
    assert uow.finding_repository.get(finding.id) is finding


def test_application_diff_budget_counts_only_returned_utf8_patch_text_and_clips_deterministically():
    finding, uow, provider, settings = context()
    provider.get_commit_diff = lambda *args, **kwargs: CommitDiffProviderResult((
        CommitDiffFile("p" * 5000, "b", "modified", "éab", True),
        CommitDiffFile("second", "second", "modified", "+later", True),
    ), "complete")
    settings.finding_diff_max_total_bytes = 3
    settings.finding_diff_max_file_bytes = 20
    result = GetFindingCommitDiff(uow, provider, SimpleNamespace(decrypt=lambda _: "token"), settings).execute(finding.id)
    assert result.files[0].diff == "éa"
    assert result.files[0].diff_truncated is True
    assert result.files[1].diff is None and result.files[1].diff_truncated is True
    assert result.total_diff_bytes == 3
    assert len(result.files[0].old_path.encode("utf-8")) == 4096
    assert result.repository_full_path == "group/repo"
