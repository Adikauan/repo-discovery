from datetime import datetime, time
from uuid import UUID

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Time, Index, text,
                        LargeBinary, String, Text, UniqueConstraint, Uuid, func)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.infrastructure.database.base import Base


class MiningExecutionRecord(Base):
    __tablename__ = 'mining_executions'
    __table_args__ = (
        CheckConstraint("trigger_type IN ('manual','scheduled')", name='ck_execution_trigger'),
        CheckConstraint("status IN ('pending','running','completed','partially_completed','failed')", name='ck_execution_status'),
        CheckConstraint('repository_count >= 0 AND successful_repository_count >= 0 AND failed_repository_count >= 0 AND finding_count >= 0', name='ck_execution_counters'),
        CheckConstraint('scope_resolution_failure_count >= 0', name='ck_execution_scope_failure_count'),
        CheckConstraint("(status = 'pending' AND started_at IS NULL AND completed_at IS NULL) OR (status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL) OR (status IN ('completed','partially_completed') AND started_at IS NOT NULL AND completed_at IS NOT NULL) OR (status = 'failed' AND completed_at IS NOT NULL)", name='ck_execution_timestamps'),
        CheckConstraint('(started_at IS NULL OR started_at >= created_at) AND (completed_at IS NULL OR completed_at >= COALESCE(started_at, created_at))', name='ck_execution_time_order'),
        CheckConstraint("(error_code IS NULL AND error_summary IS NULL) OR "
            "(status = 'failed' AND ((error_code = 'execution_interrupted' AND error_summary = 'The previous execution did not complete.') OR "
            "(error_code = 'orchestration_failed' AND error_summary = 'Execution orchestration could not be completed.') OR "
            "(error_code = 'gitlab_credential_missing' AND error_summary = 'A usable GitLab credential is unavailable.') OR "
            "(error_code = 'gitlab_instance_mismatch' AND error_summary = 'The configured GitLab instance differs from the execution snapshot.') OR "
            "(error_code = 'scope_resolution_failed' AND error_summary = 'The selected execution scope could not be resolved.'))) OR "
            "(status = 'partially_completed' AND error_code = 'scope_resolution_incomplete' AND error_summary = 'Some selected scope entries could not be resolved.')", name='ck_execution_error'),
        Index('uq_execution_active_configuration', 'monitoring_configuration_id', unique=True, postgresql_where=text("status IN ('pending','running')")),
        Index('uq_execution_scheduled_occurrence', 'monitoring_configuration_id', 'scheduled_occurrence_at', unique=True,
              postgresql_where=text("trigger_type = 'scheduled' AND scheduled_occurrence_at IS NOT NULL")),
        Index('ix_execution_newest', 'created_at', 'id'),
        Index('ix_execution_owner_history', 'monitoring_configuration_id', 'created_at', 'id'),
        Index('ix_execution_filters', 'status', 'trigger_type', 'created_at'),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    monitoring_configuration_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey('monitoring_configurations.id', ondelete='RESTRICT'), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scheduled_occurrence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    repository_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    successful_repository_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    failed_repository_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    scope_resolution_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')
    repository_mining_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_summary: Mapped[str | None] = mapped_column(String(500))
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)


class RepositoryExecutionRecord(Base):
    __tablename__ = "repository_executions"
    __table_args__ = (
        Index("uq_repository_execution_project_branch", "mining_execution_id", "gitlab_project_id", "target_branch",
              unique=True, postgresql_where=text("target_branch IS NOT NULL")),
        Index("uq_repository_execution_missing_target", "mining_execution_id", "gitlab_project_id",
              unique=True, postgresql_where=text("target_branch IS NULL")),
        CheckConstraint("gitlab_project_id > 0", name="ck_repository_execution_project_positive"),
        CheckConstraint("length(trim(repository_name)) > 0 AND length(trim(repository_full_path)) > 0", name="ck_repository_execution_names_nonempty"),
        CheckConstraint("status IN ('pending','running','completed','failed')", name="ck_repository_execution_status"),
        CheckConstraint("file_count >= 0 AND finding_count >= 0", name="ck_repository_execution_counters"),
        CheckConstraint("jsonb_typeof(observed_extensions) = 'array' AND jsonb_array_length(observed_extensions) <= 100", name="ck_repository_execution_extensions"),
        CheckConstraint("(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND ((error_code = 'repository_not_found' AND error_summary = 'The selected repository is unavailable.') OR (error_code = 'repository_forbidden' AND error_summary = 'The selected repository cannot be accessed.') OR (error_code = 'repository_timeout' AND error_summary = 'The repository request timed out.') OR (error_code = 'repository_invalid_response' AND error_summary = 'GitLab returned an invalid repository response.') OR (error_code = 'repository_default_branch_missing' AND error_summary = 'The repository has no default branch to process.') OR (error_code = 'repository_target_branch_missing' AND error_summary = 'No target branch is configured for this repository.') OR (error_code = 'repository_target_branch_unavailable' AND error_summary = 'The configured target branch is unavailable.') OR (error_code = 'target_branch_ambiguous' AND error_summary = 'Target branches could not be resolved safely for this repository.') OR (error_code = 'repository_tree_limit_exceeded' AND error_summary = 'The repository tree exceeds the configured processing limit.') OR (error_code = 'repository_processing_failed' AND error_summary = 'Repository processing could not be completed.') OR (error_code = 'commit_range_limit_exceeded' AND error_summary = 'The repository commit range exceeds the configured processing limit.') OR (error_code = 'repository_checkpoint_unreachable' AND error_summary = 'The stored repository checkpoint is no longer reachable from the selected branch.') OR (error_code = 'author_policy_ambiguous' AND error_summary = 'The configured author policy is ambiguous for this repository.')))", name="ck_repository_execution_error"),
        CheckConstraint("(status = 'pending' AND started_at IS NULL AND completed_at IS NULL) OR (status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL) OR (status IN ('completed','failed') AND started_at IS NOT NULL AND completed_at IS NOT NULL)", name="ck_repository_execution_timestamps"),
        CheckConstraint("completed_at IS NULL OR completed_at >= started_at", name="ck_repository_execution_time_order"),
        Index("ix_repository_execution_order", "mining_execution_id", "repository_full_path", "gitlab_project_id", "target_branch"),
        Index("ix_repository_execution_status", "status"),
        Index("ix_repository_execution_project", "gitlab_project_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    mining_execution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("mining_executions.id", ondelete="RESTRICT"), nullable=False)
    gitlab_project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    repository_name: Mapped[str] = mapped_column(Text, nullable=False)
    repository_full_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_branch: Mapped[str | None] = mapped_column(Text)
    processed_branch: Mapped[str | None] = mapped_column(Text)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    observed_extensions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    extensions_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_summary: Mapped[str | None] = mapped_column(String(500))


class RepositoryCheckpointRecord(Base):
    __tablename__ = "repository_checkpoints"
    __table_args__ = (
        UniqueConstraint("monitoring_configuration_id", "gitlab_project_id", "branch", name="uq_repository_checkpoint_identity"),
        CheckConstraint("gitlab_project_id > 0", name="ck_repository_checkpoint_project_positive"),
        CheckConstraint("length(trim(branch)) > 0", name="ck_repository_checkpoint_branch_nonempty"),
        CheckConstraint("last_successful_commit_hash ~ '^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$'", name="ck_repository_checkpoint_hash"),
        Index("ix_repository_checkpoint_project", "monitoring_configuration_id", "gitlab_project_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    monitoring_configuration_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("monitoring_configurations.id", ondelete="RESTRICT"), nullable=False)
    gitlab_project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    branch: Mapped[str] = mapped_column(Text, nullable=False)
    last_successful_commit_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FindingRecord(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("repository_execution_id", "rule_id", "rule_version", "commit_hash", name="uq_finding_repository_rule_commit"),
        CheckConstraint("severity = 'warning'", name="ck_finding_severity"),
        CheckConstraint("author_email_state IN ('valid','missing','malformed')", name="ck_finding_author_email_state"),
        CheckConstraint("(author_email_state = 'valid' AND author_email IS NOT NULL) OR (author_email_state IN ('missing','malformed') AND author_email IS NULL)", name="ck_finding_author_email_identity"),
        CheckConstraint("commit_hash ~ '^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$'", name="ck_finding_commit_hash"),
        CheckConstraint("(line_start IS NULL AND line_end IS NULL) OR (line_start > 0 AND line_end >= line_start)", name="ck_finding_line_range"),
        CheckConstraint("length(trim(title)) > 0 AND length(trim(summary)) > 0", name="ck_finding_text_nonempty"),
        Index("ix_finding_rule", "rule_id"), Index("ix_finding_severity", "severity"),
        Index("ix_finding_created", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    repository_execution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("repository_executions.id", ondelete="RESTRICT"), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    author_email: Mapped[str | None] = mapped_column(String(254))
    author_email_state: Mapped[str] = mapped_column(String(16), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(200))
    authored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    commit_message_summary: Mapped[str | None] = mapped_column(String(500))
    file_path: Mapped[str | None] = mapped_column(Text)
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MonitoringConfigurationRecord(Base):
    __tablename__ = "monitoring_configurations"
    __table_args__ = (CheckConstraint("revision > 0", name="ck_monitoring_configurations_revision_positive"),
                      CheckConstraint("author_policy_mode IN ('legacy','scope_aware')", name="ck_author_policy_mode"))

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    gitlab_url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allowed_author_emails: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    author_policy_mode: Mapped[str] = mapped_column(String(16), nullable=False, server_default="legacy")


class AuthorPolicyRecord(Base):
    __tablename__ = "author_policies"
    __table_args__ = (
        CheckConstraint("scope_type IN ('group','repository_branch')", name="ck_author_policy_scope_type"),
        CheckConstraint("length(instance_fingerprint) = 64", name="ck_author_policy_fingerprint"),
        CheckConstraint("length(trim(full_path)) > 0", name="ck_author_policy_path"),
        CheckConstraint("(scope_type = 'group' AND gitlab_group_id > 0 AND gitlab_project_id IS NULL AND branch IS NULL) OR (scope_type = 'repository_branch' AND gitlab_group_id IS NULL AND gitlab_project_id > 0 AND length(trim(branch)) > 0)", name="ck_author_policy_scope_shape"),
        Index("uq_author_policy_group", "monitoring_configuration_id", "instance_fingerprint", "gitlab_group_id", unique=True, postgresql_where=text("scope_type = 'group'")),
        Index("uq_author_policy_repository_branch", "monitoring_configuration_id", "instance_fingerprint", "gitlab_project_id", "branch", unique=True, postgresql_where=text("scope_type = 'repository_branch'")),
        Index("ix_author_policy_configuration", "monitoring_configuration_id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    monitoring_configuration_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("monitoring_configurations.id", ondelete="RESTRICT"), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(24), nullable=False)
    instance_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    full_path: Mapped[str] = mapped_column(Text, nullable=False)
    gitlab_group_id: Mapped[int | None] = mapped_column(BigInteger)
    gitlab_project_id: Mapped[int | None] = mapped_column(BigInteger)
    branch: Mapped[str | None] = mapped_column(Text)


class AuthorPolicyAuthorRecord(Base):
    __tablename__ = "author_policy_authors"
    __table_args__ = (
        CheckConstraint("length(trim(normalized_email)) BETWEEN 3 AND 254", name="ck_author_policy_author_email"),
    )
    policy_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("author_policies.id", ondelete="CASCADE"), primary_key=True)
    normalized_email: Mapped[str] = mapped_column(String(254), primary_key=True)
    display_email: Mapped[str] = mapped_column(String(254), nullable=False)


class CreateRequestReceiptRecord(Base):
    __tablename__ = "create_request_receipts"

    request_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GitLabCredentialRecord(Base):
    __tablename__ = "gitlab_credentials"
    __table_args__ = (
        CheckConstraint("credential_revision > 0", name="ck_gitlab_credentials_revision_positive"),
        CheckConstraint(
            "last_validation_result IS NULL OR last_validation_result IN "
            "('success','invalid_credentials','forbidden','unreachable','timeout','invalid_response','rate_limited','provider_unavailable')",
            name="ck_gitlab_credentials_validation_result",
        ),
    )

    monitoring_configuration_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("monitoring_configurations.id", ondelete="CASCADE"), primary_key=True
    )
    encrypted_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    credential_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_validation_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_validation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_url_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)


class MiningScopeStateRecord(Base):
    __tablename__ = "monitoring_configuration_scopes"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_monitoring_configuration_scopes_version_positive"),
    )

    configuration_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("monitoring_configurations.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SelectedGitLabGroupRecord(Base):
    __tablename__ = "selected_gitlab_groups"
    __table_args__ = (
        UniqueConstraint("configuration_id", "instance_fingerprint", "gitlab_group_id",
                         name="uq_selected_gitlab_groups_origin_entity"),
        CheckConstraint("gitlab_group_id > 0", name="ck_selected_gitlab_groups_id_positive"),
        CheckConstraint("parent_group_id IS NULL OR parent_group_id > 0",
                        name="ck_selected_gitlab_groups_parent_id_positive"),
        CheckConstraint("length(instance_fingerprint) = 64",
                        name="ck_selected_gitlab_groups_fingerprint_length"),
    )

    selection_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    configuration_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("monitoring_configuration_scopes.configuration_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    instance_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    gitlab_group_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    full_path: Mapped[str] = mapped_column(Text, nullable=False)
    parent_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SelectedGitLabRepositoryRecord(Base):
    __tablename__ = "selected_gitlab_repositories"
    __table_args__ = (
        UniqueConstraint("configuration_id", "instance_fingerprint", "gitlab_project_id",
                         name="uq_selected_gitlab_repositories_origin_entity"),
        CheckConstraint("gitlab_project_id > 0", name="ck_selected_gitlab_repositories_id_positive"),
        CheckConstraint("parent_group_id IS NULL OR parent_group_id > 0",
                        name="ck_selected_gitlab_repositories_parent_id_positive"),
        CheckConstraint("length(instance_fingerprint) = 64",
                        name="ck_selected_gitlab_repositories_fingerprint_length"),
    )

    selection_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    configuration_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("monitoring_configuration_scopes.configuration_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    instance_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    gitlab_project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    full_path: Mapped[str] = mapped_column(Text, nullable=False)
    parent_group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MonitoringScheduleRecord(Base):
    __tablename__ = "monitoring_schedules"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_monitoring_schedules_version_positive"),
        CheckConstraint(
            "(configured = false AND recurrence_type IS NULL AND enabled IS NULL AND execution_time IS NULL "
            "AND timezone IS NULL AND day_of_week IS NULL AND day_of_month IS NULL AND created_at IS NULL) OR "
            "(configured = true AND recurrence_type IS NOT NULL AND enabled IS NOT NULL AND execution_time IS NOT NULL "
            "AND timezone IS NOT NULL AND created_at IS NOT NULL)",
            name="ck_monitoring_schedules_configured_payload",
        ),
        CheckConstraint(
            "(configured = false) OR "
            "(recurrence_type = 'daily' AND day_of_week IS NULL AND day_of_month IS NULL) OR "
            "(recurrence_type = 'weekly' AND day_of_week BETWEEN 1 AND 7 AND day_of_month IS NULL) OR "
            "(recurrence_type = 'monthly' AND day_of_month BETWEEN 1 AND 31 AND day_of_week IS NULL)",
            name="ck_monitoring_schedules_recurrence_fields",
        ),
        CheckConstraint("recurrence_type IS NULL OR recurrence_type IN ('daily','weekly','monthly')",
                        name="ck_monitoring_schedules_recurrence_type"),
    )

    monitoring_configuration_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("monitoring_configurations.id", ondelete="CASCADE"), primary_key=True
    )
    configured: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    recurrence_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    execution_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
