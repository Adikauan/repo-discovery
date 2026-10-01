"""Remove interim Scope branch rules; Repository + Branch Policies are authoritative."""
from alembic import op


revision = "0011_policy_mining_targets"
down_revision = "0010_repository_target_branches"
branch_labels = None
depends_on = None


def upgrade():
    # Do not convert these rows: they have no branch-specific allowed-author list.
    op.drop_index("ix_target_branch_rule_configuration", table_name="target_branch_rules")
    op.drop_table("target_branch_rules")


def downgrade():
    # Restoring empty storage does not recreate obsolete rule data.
    from sqlalchemy.dialects import postgresql
    import sqlalchemy as sa

    op.create_table(
        "target_branch_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("monitoring_configuration_id", postgresql.UUID(as_uuid=True), nullable=False),
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
