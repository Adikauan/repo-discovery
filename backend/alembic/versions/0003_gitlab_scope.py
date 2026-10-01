"""Persist explicit GitLab group and repository scope rules."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_gitlab_scope"
down_revision = "0002_gitlab_credentials"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monitoring_configuration_scopes",
        sa.Column("configuration_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("monitoring_configurations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_monitoring_configuration_scopes_version_positive"),
    )
    for table, entity_id, constraint_prefix in (
        ("selected_gitlab_groups", "gitlab_group_id", "groups"),
        ("selected_gitlab_repositories", "gitlab_project_id", "repositories"),
    ):
        op.create_table(
            table,
            sa.Column("selection_id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("configuration_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("monitoring_configuration_scopes.configuration_id", ondelete="CASCADE"),
                      nullable=False),
            sa.Column("instance_fingerprint", sa.String(64), nullable=False),
            sa.Column(entity_id, sa.BigInteger(), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("full_path", sa.Text(), nullable=False),
            sa.Column("parent_group_id", sa.BigInteger(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("configuration_id", "instance_fingerprint", entity_id,
                                name=f"uq_selected_gitlab_{constraint_prefix}_origin_entity"),
            sa.CheckConstraint(f"{entity_id} > 0", name=f"ck_selected_gitlab_{constraint_prefix}_id_positive"),
            sa.CheckConstraint("parent_group_id IS NULL OR parent_group_id > 0",
                               name=f"ck_selected_gitlab_{constraint_prefix}_parent_id_positive"),
            sa.CheckConstraint("length(instance_fingerprint) = 64",
                               name=f"ck_selected_gitlab_{constraint_prefix}_fingerprint_length"),
        )
        op.create_index(f"ix_{table}_configuration_id", table, ["configuration_id"])


def downgrade():
    op.drop_index("ix_selected_gitlab_repositories_configuration_id", table_name="selected_gitlab_repositories")
    op.drop_table("selected_gitlab_repositories")
    op.drop_index("ix_selected_gitlab_groups_configuration_id", table_name="selected_gitlab_groups")
    op.drop_table("selected_gitlab_groups")
    op.drop_table("monitoring_configuration_scopes")
