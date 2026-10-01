from datetime import UTC, datetime
from dataclasses import replace
import logging
from uuid import uuid4

from app.domain.entities.repository_execution import RepositoryExecution
from app.domain.services.repository_summary_rule import RepositorySummaryRule
from app.domain.value_objects.mining_failure import MiningFailure
from app.domain.value_objects.repository_context import RepositoryContext
from app.domain.services.unauthorized_commit_author_rule import UnauthorizedCommitAuthorRule
from app.domain.entities.finding import Finding
from app.domain.entities.repository_checkpoint import RepositoryCheckpoint
from app.domain.services.author_policy_resolver import AuthorPolicyResolutionError, resolve_author_policy

logger = logging.getLogger(__name__)


class ProcessRepository:
    def __init__(self, uow, provider, *, clock=None, max_file_bytes=1_048_576, max_extensions=100,
                 max_commits=1000):
        self.uow = uow
        self.provider = provider
        self.clock = clock or (lambda: datetime.now(UTC))
        self.max_file_bytes = max_file_bytes
        self.max_extensions = max_extensions
        self.max_commits = max_commits
        self.rule = RepositorySummaryRule()
        self.author_rule = UnauthorizedCommitAuthorRule()

    @staticmethod
    def _target_branch_call(operation):
        try:
            return operation()
        except MiningFailure as error:
            if error.code in {"repository_not_found", "repository_default_branch_missing"}:
                raise MiningFailure("repository_target_branch_unavailable") from error
            raise

    def execute(self, row: RepositoryExecution, snapshot, token, *, preflight_error_code=None):
        repo = self.uow.repository_execution_repository
        running = row.transition("running", self.clock(), expected_status="pending")
        if not repo.transition(running, "pending"):
            raise RuntimeError("Repository lifecycle changed.")
        self.uow.commit()
        try:
            if preflight_error_code:
                raise MiningFailure(preflight_error_code)
            if not row.target_branch:
                raise MiningFailure("repository_target_branch_missing")
            project = self.provider.project(snapshot.gitlab_url, token, row.gitlab_project_id)
            branch = row.target_branch
            files = self._target_branch_call(lambda: self.provider.tree(
                snapshot.gitlab_url, token, row.gitlab_project_id, branch))
            context = RepositoryContext(row.gitlab_project_id, project["name"], project["full_path"],
                                        branch, files, self.max_file_bytes)
            summary = self.rule.execute(context, max_extensions=self.max_extensions)
            head_commit = self._target_branch_call(lambda: self.provider.get_branch_head(
                snapshot.gitlab_url, token, row.gitlab_project_id, branch))
            head = head_commit.commit_hash
            checkpoint_repo = getattr(self.uow, "repository_checkpoint_repository", None)
            finding_repo = getattr(self.uow, "finding_repository", None)
            checkpoint = checkpoint_repo.get(snapshot.configuration_id, row.gitlab_project_id,
                                             branch) if checkpoint_repo else None
            # End the read transaction before any further provider calls.
            self.uow.commit()
            if checkpoint is None:
                commits = ()
            else:
                if not self.provider.is_commit_reachable(snapshot.gitlab_url, token, row.gitlab_project_id,
                                                          checkpoint.last_successful_commit_hash, branch):
                    raise MiningFailure("repository_checkpoint_unreachable")
                commits = () if checkpoint.last_successful_commit_hash.lower() == head.lower() else \
                    self._target_branch_call(lambda: self.provider.list_commits_after(
                        snapshot.gitlab_url, token, row.gitlab_project_id, branch,
                        checkpoint.last_successful_commit_hash, head, max_items=self.max_commits))
            try:
                policy = resolve_author_policy(snapshot, row.gitlab_project_id, row.repository_full_path,
                                              branch)
            except AuthorPolicyResolutionError as error:
                logger.error("Ambiguous author policy for repository execution", extra={
                    "repository_execution_id": str(row.id), "gitlab_project_id": row.gitlab_project_id,
                    "error_code": error.code,
                })
                raise MiningFailure(error.code) from error
            candidates = self.author_rule.execute(commits, policy.allowed_author_emails) \
                if policy.allowed_author_emails is not None else ()
            checkpoint_item = RepositoryCheckpoint(
                id=uuid4(), monitoring_configuration_id=snapshot.configuration_id,
                gitlab_project_id=row.gitlab_project_id, branch=branch,
                last_successful_commit_hash=head, updated_at=self.clock())
            if finding_repo is not None:
                for candidate in candidates:
                    finding_repo.add(Finding(
                        id=uuid4(), repository_execution_id=row.id,
                        rule_id=candidate.rule_id, rule_version=candidate.rule_version,
                        severity=candidate.severity, title=candidate.title, summary=candidate.summary,
                        commit_hash=candidate.commit_hash, author_email=candidate.author_email,
                        author_email_state=candidate.author_email_state, author_name=candidate.author_name,
                        authored_at=candidate.authored_at, commit_message_summary=candidate.commit_message_summary,
                        file_path=candidate.file_path, line_start=candidate.line_start, line_end=candidate.line_end,
                        created_at=self.clock()))
            completed = replace(running.with_summary(summary), finding_count=len(candidates)).transition(
                "completed", self.clock(), expected_status="running")
            if not repo.transition(completed, "running"):
                raise RuntimeError("Repository lifecycle changed.")
            if checkpoint_repo is not None:
                checkpoint_repo.put(checkpoint_item)
            self.uow.commit()
            return completed
        except MiningFailure as failure:
            self.uow.rollback()
            failed = running.fail(failure.code, self.clock())
            if not repo.transition(failed, "running"):
                raise RuntimeError("Repository lifecycle changed.")
            self.uow.commit()
            return failed
        except Exception:
            self.uow.rollback()
            failed = running.fail("repository_processing_failed", self.clock())
            if not repo.transition(failed, "running"):
                raise RuntimeError("Repository lifecycle changed.")
            self.uow.commit()
            return failed
