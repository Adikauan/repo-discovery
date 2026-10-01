"""Add durable per-repository execution results."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_repository_executions"
down_revision = "0005_mining_executions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mining_executions", sa.Column("scope_resolution_failure_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("mining_executions", sa.Column("repository_mining_completed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_check_constraint("ck_execution_scope_failure_count", "mining_executions", "scope_resolution_failure_count >= 0")
    op.drop_constraint("ck_execution_error", "mining_executions", type_="check")
    op.create_check_constraint("ck_execution_error", "mining_executions",
        "(error_code IS NULL AND error_summary IS NULL) OR "
        "(status = 'failed' AND ((error_code = 'execution_interrupted' AND error_summary = 'The previous execution did not complete.') OR "
        "(error_code = 'orchestration_failed' AND error_summary = 'Execution orchestration could not be completed.') OR "
        "(error_code = 'gitlab_credential_missing' AND error_summary = 'A usable GitLab credential is unavailable.') OR "
        "(error_code = 'gitlab_instance_mismatch' AND error_summary = 'The configured GitLab instance differs from the execution snapshot.') OR "
        "(error_code = 'scope_resolution_failed' AND error_summary = 'The selected execution scope could not be resolved.'))) OR "
        "(status = 'partially_completed' AND error_code = 'scope_resolution_incomplete' AND error_summary = 'Some selected scope entries could not be resolved.')")
    op.create_table("repository_executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mining_execution_id", sa.Uuid(), sa.ForeignKey("mining_executions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("gitlab_project_id", sa.BigInteger(), nullable=False),
        sa.Column("repository_name", sa.Text(), nullable=False),
        sa.Column("repository_full_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("processed_branch", sa.Text()),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observed_extensions", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("extensions_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("finding_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_summary", sa.String(500)),
        sa.CheckConstraint("gitlab_project_id > 0", name="ck_repository_execution_project_positive"),
        sa.CheckConstraint("length(trim(repository_name)) > 0 AND length(trim(repository_full_path)) > 0", name="ck_repository_execution_names_nonempty"),
        sa.CheckConstraint("status IN ('pending','running','completed','failed')", name="ck_repository_execution_status"),
        sa.CheckConstraint("file_count >= 0 AND finding_count >= 0", name="ck_repository_execution_counters"),
        sa.CheckConstraint("jsonb_typeof(observed_extensions) = 'array' AND jsonb_array_length(observed_extensions) <= 100", name="ck_repository_execution_extensions"),
        sa.CheckConstraint("(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND ((error_code = 'repository_not_found' AND error_summary = 'The selected repository is unavailable.') OR (error_code = 'repository_forbidden' AND error_summary = 'The selected repository cannot be accessed.') OR (error_code = 'repository_timeout' AND error_summary = 'The repository request timed out.') OR (error_code = 'repository_invalid_response' AND error_summary = 'GitLab returned an invalid repository response.') OR (error_code = 'repository_default_branch_missing' AND error_summary = 'The repository has no default branch to process.') OR (error_code = 'repository_tree_limit_exceeded' AND error_summary = 'The repository tree exceeds the configured processing limit.') OR (error_code = 'repository_processing_failed' AND error_summary = 'Repository processing could not be completed.')))", name="ck_repository_execution_error"),
        sa.CheckConstraint("(status = 'pending' AND started_at IS NULL AND completed_at IS NULL) OR (status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL) OR (status IN ('completed','failed') AND started_at IS NOT NULL AND completed_at IS NOT NULL)", name="ck_repository_execution_timestamps"),
        sa.CheckConstraint("completed_at IS NULL OR completed_at >= started_at", name="ck_repository_execution_time_order"),
        sa.UniqueConstraint("mining_execution_id", "gitlab_project_id", name="uq_repository_execution_project"))
    op.create_index("ix_repository_execution_order", "repository_executions", ["mining_execution_id", "repository_full_path", "gitlab_project_id"])
    op.create_index("ix_repository_execution_status", "repository_executions", ["status"])
    op.create_index("ix_repository_execution_project", "repository_executions", ["gitlab_project_id"])


def downgrade():
    op.drop_index("ix_repository_execution_project", table_name="repository_executions")
    op.drop_index("ix_repository_execution_status", table_name="repository_executions")
    op.drop_index("ix_repository_execution_order", table_name="repository_executions")
    op.drop_table("repository_executions")
    op.drop_constraint("ck_execution_error", "mining_executions", type_="check")
    op.create_check_constraint("ck_execution_error", "mining_executions", "(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND error_code IS NOT NULL AND error_summary IS NOT NULL)")
    op.drop_constraint("ck_execution_scope_failure_count", "mining_executions", type_="check")
    op.drop_column("mining_executions", "repository_mining_completed")
    op.drop_column("mining_executions", "scope_resolution_failure_count")
