"""Persist allowed commit authors, checkpoints, and immutable mining findings."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_mining_findings"
down_revision = "0007_sched_exec_idem"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("monitoring_configurations", sa.Column(
        "allowed_author_emails", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.drop_constraint("ck_repository_execution_error", "repository_executions", type_="check")
    op.create_check_constraint("ck_repository_execution_error", "repository_executions",
        "(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND ((error_code = 'repository_not_found' AND error_summary = 'The selected repository is unavailable.') OR (error_code = 'repository_forbidden' AND error_summary = 'The selected repository cannot be accessed.') OR (error_code = 'repository_timeout' AND error_summary = 'The repository request timed out.') OR (error_code = 'repository_invalid_response' AND error_summary = 'GitLab returned an invalid repository response.') OR (error_code = 'repository_default_branch_missing' AND error_summary = 'The repository has no default branch to process.') OR (error_code = 'repository_tree_limit_exceeded' AND error_summary = 'The repository tree exceeds the configured processing limit.') OR (error_code = 'repository_processing_failed' AND error_summary = 'Repository processing could not be completed.') OR (error_code = 'commit_range_limit_exceeded' AND error_summary = 'The repository commit range exceeds the configured processing limit.') OR (error_code = 'repository_checkpoint_unreachable' AND error_summary = 'The stored repository checkpoint is no longer reachable from the selected branch.')))")
    op.create_table("repository_checkpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("monitoring_configuration_id", sa.Uuid(), nullable=False),
        sa.Column("gitlab_project_id", sa.BigInteger(), nullable=False),
        sa.Column("branch", sa.Text(), nullable=False),
        sa.Column("last_successful_commit_hash", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("gitlab_project_id > 0", name="ck_repository_checkpoint_project_positive"),
        sa.CheckConstraint("length(trim(branch)) > 0", name="ck_repository_checkpoint_branch_nonempty"),
        sa.CheckConstraint("last_successful_commit_hash ~ '^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$'", name="ck_repository_checkpoint_hash"),
        sa.ForeignKeyConstraint(["monitoring_configuration_id"], ["monitoring_configurations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("monitoring_configuration_id", "gitlab_project_id", "branch", name="uq_repository_checkpoint_identity"))
    op.create_index("ix_repository_checkpoint_project", "repository_checkpoints", ["monitoring_configuration_id", "gitlab_project_id"])
    op.create_table("findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_execution_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("commit_hash", sa.String(64), nullable=False),
        sa.Column("author_email", sa.String(254)),
        sa.Column("author_email_state", sa.String(16), nullable=False),
        sa.Column("author_name", sa.String(200)),
        sa.Column("authored_at", sa.DateTime(timezone=True)),
        sa.Column("commit_message_summary", sa.String(500)),
        sa.Column("file_path", sa.Text()),
        sa.Column("line_start", sa.Integer()),
        sa.Column("line_end", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("severity = 'warning'", name="ck_finding_severity"),
        sa.CheckConstraint("author_email_state IN ('valid','missing','malformed')", name="ck_finding_author_email_state"),
        sa.CheckConstraint("(author_email_state = 'valid' AND author_email IS NOT NULL) OR (author_email_state IN ('missing','malformed') AND author_email IS NULL)", name="ck_finding_author_email_identity"),
        sa.CheckConstraint("commit_hash ~ '^[0-9a-fA-F]{40}([0-9a-fA-F]{24})?$'", name="ck_finding_commit_hash"),
        sa.CheckConstraint("(line_start IS NULL AND line_end IS NULL) OR (line_start > 0 AND line_end >= line_start)", name="ck_finding_line_range"),
        sa.CheckConstraint("length(trim(title)) > 0 AND length(trim(summary)) > 0", name="ck_finding_text_nonempty"),
        sa.ForeignKeyConstraint(["repository_execution_id"], ["repository_executions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_execution_id", "rule_id", "rule_version", "commit_hash", name="uq_finding_repository_rule_commit"))
    op.create_index("ix_findings_repository_execution_id", "findings", ["repository_execution_id"])
    op.create_index("ix_finding_rule", "findings", ["rule_id"])
    op.create_index("ix_finding_severity", "findings", ["severity"])
    op.create_index("ix_finding_created", "findings", ["created_at", "id"])


def downgrade():
    op.drop_index("ix_finding_created", table_name="findings")
    op.drop_index("ix_finding_severity", table_name="findings")
    op.drop_index("ix_finding_rule", table_name="findings")
    op.drop_index("ix_findings_repository_execution_id", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_repository_checkpoint_project", table_name="repository_checkpoints")
    op.drop_table("repository_checkpoints")
    op.drop_constraint("ck_repository_execution_error", "repository_executions", type_="check")
    op.create_check_constraint("ck_repository_execution_error", "repository_executions",
        "(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND ((error_code = 'repository_not_found' AND error_summary = 'The selected repository is unavailable.') OR (error_code = 'repository_forbidden' AND error_summary = 'The selected repository cannot be accessed.') OR (error_code = 'repository_timeout' AND error_summary = 'The repository request timed out.') OR (error_code = 'repository_invalid_response' AND error_summary = 'GitLab returned an invalid repository response.') OR (error_code = 'repository_default_branch_missing' AND error_summary = 'The repository has no default branch to process.') OR (error_code = 'repository_tree_limit_exceeded' AND error_summary = 'The repository tree exceeds the configured processing limit.') OR (error_code = 'repository_processing_failed' AND error_summary = 'Repository processing could not be completed.')))")
    op.drop_column("monitoring_configurations", "allowed_author_emails")
