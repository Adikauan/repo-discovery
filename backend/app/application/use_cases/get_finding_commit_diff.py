from app.application.use_cases.get_gitlab_connection_status import normalized_url_fingerprint
from app.config import get_settings
from app.domain.errors import CommitDiffError, CredentialServiceUnavailable
from app.domain.value_objects.commit_diff import CommitDiffDetails, normalize_commit_diff


UNAUTHORIZED_AUTHOR_RULES = {"unauthorized_commit_author", "unauthorized-commit-author"}


class GetFindingCommitDiff:
    """Read a Finding-owned historical commit diff from its snapshot-bound GitLab instance."""
    def __init__(self, uow, provider, cipher, settings=None):
        self.uow, self.provider, self.cipher = uow, provider, cipher
        self.settings = settings or get_settings()

    def execute(self, finding_id):
        finding = self.uow.finding_repository.get(finding_id)
        if finding is None:
            raise CommitDiffError("finding_not_found")
        if finding.rule_id not in UNAUTHORIZED_AUTHOR_RULES or not finding.commit_hash:
            raise CommitDiffError("finding_diff_not_applicable")
        repository = self.uow.repository_execution_repository.get(finding.repository_execution_id)
        execution = self.uow.execution_repository.get(repository.mining_execution_id) if repository else None
        if repository is None or execution is None or not repository.gitlab_project_id:
            raise CommitDiffError("finding_diff_not_applicable")

        snapshot_url = execution.snapshot.gitlab_url
        fingerprint = normalized_url_fingerprint(snapshot_url)
        configuration = self.uow.configuration_repository.get(execution.monitoring_configuration_id)
        if configuration is None or normalized_url_fingerprint(configuration.gitlab_url) != fingerprint:
            raise CommitDiffError("gitlab_instance_mismatch")
        credential = self.uow.credential_repository.get(execution.monitoring_configuration_id)
        if credential is None or credential.last_validation_result != "success" or credential.validated_url_fingerprint != fingerprint or self.cipher is None:
            raise CommitDiffError("gitlab_credential_missing")
        try:
            token = self.cipher.decrypt(credential.encrypted_token)
        except CredentialServiceUnavailable as error:
            raise CommitDiffError("gitlab_credential_missing") from error
        if not token:
            raise CommitDiffError("gitlab_credential_missing")

        provider_result = self.provider.get_commit_diff(snapshot_url, token, repository.gitlab_project_id,
            finding.commit_hash, max_files=self.settings.finding_diff_max_files)
        bounded = normalize_commit_diff(provider_result.files, provider_result.files_completeness,
            max_files=self.settings.finding_diff_max_files,
            max_file_bytes=self.settings.finding_diff_max_file_bytes,
            max_total_bytes=self.settings.finding_diff_max_total_bytes,
            max_path_bytes=self.settings.finding_diff_max_path_bytes)
        name, _ = _bounded(repository.repository_name, 200)
        path, _ = _bounded(repository.repository_full_path, self.settings.finding_diff_max_path_bytes)
        return CommitDiffDetails(finding.id, name, len(repository.repository_name.encode("utf-8")) > 200,
            path, len(repository.repository_full_path.encode("utf-8")) > self.settings.finding_diff_max_path_bytes,
            finding.commit_hash, finding.author_name, finding.author_email, finding.authored_at,
            finding.commit_message_summary, bounded.files, bounded.files_completeness, bounded.total_diff_bytes)


def _bounded(value, limit):
    from app.domain.value_objects.commit_diff import bound_utf8
    bounded, _ = bound_utf8(value, limit)
    return bounded or "", bounded != value
