"""Persist scope-aware author policies without dropping legacy allowlists."""
from alembic import op
import sqlalchemy as sa

revision = "0009_author_policies"
down_revision = "0008_mining_findings"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_repository_execution_error", "repository_executions", type_="check")
    op.create_check_constraint("ck_repository_execution_error", "repository_executions",
        "(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND ((error_code = 'repository_not_found' AND error_summary = 'The selected repository is unavailable.') OR (error_code = 'repository_forbidden' AND error_summary = 'The selected repository cannot be accessed.') OR (error_code = 'repository_timeout' AND error_summary = 'The repository request timed out.') OR (error_code = 'repository_invalid_response' AND error_summary = 'GitLab returned an invalid repository response.') OR (error_code = 'repository_default_branch_missing' AND error_summary = 'The repository has no default branch to process.') OR (error_code = 'repository_tree_limit_exceeded' AND error_summary = 'The repository tree exceeds the configured processing limit.') OR (error_code = 'repository_processing_failed' AND error_summary = 'Repository processing could not be completed.') OR (error_code = 'commit_range_limit_exceeded' AND error_summary = 'The repository commit range exceeds the configured processing limit.') OR (error_code = 'repository_checkpoint_unreachable' AND error_summary = 'The stored repository checkpoint is no longer reachable from the selected branch.') OR (error_code = 'author_policy_ambiguous' AND error_summary = 'The configured author policy is ambiguous for this repository.'))) ")
    op.add_column("monitoring_configurations", sa.Column(
        "author_policy_mode", sa.String(16), nullable=False, server_default="legacy"))
    op.create_check_constraint("ck_author_policy_mode", "monitoring_configurations",
                               "author_policy_mode IN ('legacy','scope_aware')")
    op.create_table(
        "author_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("monitoring_configuration_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(24), nullable=False),
        sa.Column("instance_fingerprint", sa.String(64), nullable=False),
        sa.Column("full_path", sa.Text(), nullable=False),
        sa.Column("gitlab_group_id", sa.BigInteger(), nullable=True),
        sa.Column("gitlab_project_id", sa.BigInteger(), nullable=True),
        sa.Column("branch", sa.Text(), nullable=True),
        sa.CheckConstraint("scope_type IN ('group','repository_branch')", name="ck_author_policy_scope_type"),
        sa.CheckConstraint("length(instance_fingerprint) = 64", name="ck_author_policy_fingerprint"),
        sa.CheckConstraint("length(trim(full_path)) > 0", name="ck_author_policy_path"),
        sa.CheckConstraint("(scope_type = 'group' AND gitlab_group_id > 0 AND gitlab_project_id IS NULL AND branch IS NULL) OR (scope_type = 'repository_branch' AND gitlab_group_id IS NULL AND gitlab_project_id > 0 AND length(trim(branch)) > 0)", name="ck_author_policy_scope_shape"),
        sa.ForeignKeyConstraint(["monitoring_configuration_id"], ["monitoring_configurations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_author_policy_group", "author_policies",
                    ["monitoring_configuration_id", "instance_fingerprint", "gitlab_group_id"],
                    unique=True, postgresql_where=sa.text("scope_type = 'group'"))
    op.create_index("uq_author_policy_repository_branch", "author_policies",
                    ["monitoring_configuration_id", "instance_fingerprint", "gitlab_project_id", "branch"],
                    unique=True, postgresql_where=sa.text("scope_type = 'repository_branch'"))
    op.create_index("ix_author_policy_configuration", "author_policies", ["monitoring_configuration_id"])
    op.create_table(
        "author_policy_authors",
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_email", sa.String(254), nullable=False),
        sa.Column("display_email", sa.String(254), nullable=False),
        sa.CheckConstraint("length(trim(normalized_email)) BETWEEN 3 AND 254", name="ck_author_policy_author_email"),
        sa.ForeignKeyConstraint(["policy_id"], ["author_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("policy_id", "normalized_email"),
    )


def downgrade():
    op.drop_table("author_policy_authors")
    op.drop_index("ix_author_policy_configuration", table_name="author_policies")
    op.drop_index("uq_author_policy_repository_branch", table_name="author_policies")
    op.drop_index("uq_author_policy_group", table_name="author_policies")
    op.drop_table("author_policies")
    op.drop_constraint("ck_author_policy_mode", "monitoring_configurations", type_="check")
    op.drop_column("monitoring_configurations", "author_policy_mode")
    op.drop_constraint("ck_repository_execution_error", "repository_executions", type_="check")
    op.create_check_constraint("ck_repository_execution_error", "repository_executions",
        "(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND ((error_code = 'repository_not_found' AND error_summary = 'The selected repository is unavailable.') OR (error_code = 'repository_forbidden' AND error_summary = 'The selected repository cannot be accessed.') OR (error_code = 'repository_timeout' AND error_summary = 'The repository request timed out.') OR (error_code = 'repository_invalid_response' AND error_summary = 'GitLab returned an invalid repository response.') OR (error_code = 'repository_default_branch_missing' AND error_summary = 'The repository has no default branch to process.') OR (error_code = 'repository_tree_limit_exceeded' AND error_summary = 'The repository tree exceeds the configured processing limit.') OR (error_code = 'repository_processing_failed' AND error_summary = 'Repository processing could not be completed.') OR (error_code = 'commit_range_limit_exceeded' AND error_summary = 'The repository commit range exceeds the configured processing limit.') OR (error_code = 'repository_checkpoint_unreachable' AND error_summary = 'The stored repository checkpoint is no longer reachable from the selected branch.'))) ")
