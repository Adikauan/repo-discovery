"""Add explicit repository/group branch targets and sanitize legacy checkpoints."""
from alembic import op
import sqlalchemy as sa


revision = "0010_repository_target_branches"
down_revision = "0009_author_policies"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "target_branch_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("monitoring_configuration_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("instance_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("gitlab_scope_id", sa.BigInteger(), nullable=False),
        sa.Column("full_path", sa.Text(), nullable=False),
        sa.Column("branch_name", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("scope_type IN ('group','repository')", name="ck_target_branch_scope_type"),
        sa.CheckConstraint("length(instance_fingerprint) = 64", name="ck_target_branch_fingerprint"),
        sa.CheckConstraint("gitlab_scope_id > 0", name="ck_target_branch_scope_id_positive"),
        sa.CheckConstraint("length(trim(full_path)) > 0", name="ck_target_branch_full_path"),
        sa.CheckConstraint("length(trim(branch_name)) > 0", name="ck_target_branch_name"),
        sa.ForeignKeyConstraint(["monitoring_configuration_id"], ["monitoring_configurations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("monitoring_configuration_id", "instance_fingerprint", "scope_type",
                            "gitlab_scope_id", "branch_name", name="uq_target_branch_rule_identity"),
    )
    op.create_index("ix_target_branch_rule_configuration", "target_branch_rules", ["monitoring_configuration_id"])

    op.add_column("repository_executions", sa.Column("target_branch", sa.Text(), nullable=True))
    op.drop_index("ix_repository_execution_order", table_name="repository_executions")
    op.create_index("ix_repository_execution_order", "repository_executions",
                    ["mining_execution_id", "repository_full_path", "gitlab_project_id", "target_branch"])
    op.drop_constraint("uq_repository_execution_project", "repository_executions", type_="unique")
    # PostgreSQL UNIQUE constraints treat NULL values as distinct. Use two partial
    # indexes so missing-target preflight rows remain unique as well as each branch.
    op.create_index("uq_repository_execution_project_branch", "repository_executions",
                    ["mining_execution_id", "gitlab_project_id", "target_branch"], unique=True,
                    postgresql_where=sa.text("target_branch IS NOT NULL"))
    op.create_index("uq_repository_execution_missing_target", "repository_executions",
                    ["mining_execution_id", "gitlab_project_id"], unique=True,
                    postgresql_where=sa.text("target_branch IS NULL"))

    op.drop_constraint("ck_repository_execution_error", "repository_executions", type_="check")
    op.create_check_constraint("ck_repository_execution_error", "repository_executions",
        "(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND ((error_code = 'repository_not_found' AND error_summary = 'The selected repository is unavailable.') OR (error_code = 'repository_forbidden' AND error_summary = 'The selected repository cannot be accessed.') OR (error_code = 'repository_timeout' AND error_summary = 'The repository request timed out.') OR (error_code = 'repository_invalid_response' AND error_summary = 'GitLab returned an invalid repository response.') OR (error_code = 'repository_default_branch_missing' AND error_summary = 'The repository has no default branch to process.') OR (error_code = 'repository_target_branch_missing' AND error_summary = 'No target branch is configured for this repository.') OR (error_code = 'repository_target_branch_unavailable' AND error_summary = 'The configured target branch is unavailable.') OR (error_code = 'target_branch_ambiguous' AND error_summary = 'Target branches could not be resolved safely for this repository.') OR (error_code = 'repository_tree_limit_exceeded' AND error_summary = 'The repository tree exceeds the configured processing limit.') OR (error_code = 'repository_processing_failed' AND error_summary = 'Repository processing could not be completed.') OR (error_code = 'commit_range_limit_exceeded' AND error_summary = 'The repository commit range exceeds the configured processing limit.') OR (error_code = 'repository_checkpoint_unreachable' AND error_summary = 'The stored repository checkpoint is no longer reachable from the selected branch.') OR (error_code = 'author_policy_ambiguous' AND error_summary = 'The configured author policy is ambiguous for this repository.')))"
    )

    # Old checkpoints were advanced using GitLab default_branch. Their provenance
    # cannot establish an explicit target rule, so none may seed Feature 017.
    op.execute(sa.text("DELETE FROM repository_checkpoints"))


def downgrade():
    # Checkpoints deleted during upgrade cannot be reconstructed. Schema downgrade
    # does not restore or fabricate them.
    bind = op.get_bind()
    duplicate = bind.execute(sa.text("""
        SELECT 1 FROM repository_executions
        GROUP BY mining_execution_id, gitlab_project_id HAVING COUNT(*) > 1 LIMIT 1
    """)).first()
    if duplicate:
        raise RuntimeError("Cannot downgrade Feature 017 while executions contain multiple branches per repository.")
    op.drop_constraint("ck_repository_execution_error", "repository_executions", type_="check")
    op.create_check_constraint("ck_repository_execution_error", "repository_executions",
        "(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND ((error_code = 'repository_not_found' AND error_summary = 'The selected repository is unavailable.') OR (error_code = 'repository_forbidden' AND error_summary = 'The selected repository cannot be accessed.') OR (error_code = 'repository_timeout' AND error_summary = 'The repository request timed out.') OR (error_code = 'repository_invalid_response' AND error_summary = 'GitLab returned an invalid repository response.') OR (error_code = 'repository_default_branch_missing' AND error_summary = 'The repository has no default branch to process.') OR (error_code = 'repository_tree_limit_exceeded' AND error_summary = 'The repository tree exceeds the configured processing limit.') OR (error_code = 'repository_processing_failed' AND error_summary = 'Repository processing could not be completed.') OR (error_code = 'commit_range_limit_exceeded' AND error_summary = 'The repository commit range exceeds the configured processing limit.') OR (error_code = 'repository_checkpoint_unreachable' AND error_summary = 'The stored repository checkpoint is no longer reachable from the selected branch.') OR (error_code = 'author_policy_ambiguous' AND error_summary = 'The configured author policy is ambiguous for this repository.')))"
    )
    constraint_names = {item["name"] for item in sa.inspect(bind).get_unique_constraints("repository_executions")}
    if "uq_repository_execution_project_branch" in constraint_names:
        # Development databases may already have applied the earlier draft of
        # this not-yet-released migration, which represented this key as a constraint.
        op.drop_constraint("uq_repository_execution_project_branch", "repository_executions", type_="unique")
    else:
        op.drop_index("uq_repository_execution_project_branch", table_name="repository_executions")
    index_names = {item["name"] for item in sa.inspect(bind).get_indexes("repository_executions")}
    if "uq_repository_execution_missing_target" in index_names:
        op.drop_index("uq_repository_execution_missing_target", table_name="repository_executions")
    op.create_unique_constraint("uq_repository_execution_project", "repository_executions",
                                ["mining_execution_id", "gitlab_project_id"])
    op.drop_index("ix_repository_execution_order", table_name="repository_executions")
    op.drop_column("repository_executions", "target_branch")
    op.create_index("ix_repository_execution_order", "repository_executions",
                    ["mining_execution_id", "repository_full_path", "gitlab_project_id"])
    op.drop_index("ix_target_branch_rule_configuration", table_name="target_branch_rules")
    op.drop_table("target_branch_rules")
