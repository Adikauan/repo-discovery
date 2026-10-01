"""Create monitoring configurations and create receipts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_monitoring_configurations"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monitoring_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("gitlab_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("revision > 0", name="ck_monitoring_configurations_revision_positive"),
    )
    op.create_index("ix_monitoring_configurations_name", "monitoring_configurations", ["name"])
    op.create_table(
        "create_request_receipts",
        sa.Column("request_key", sa.String(128), primary_key=True),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("response_snapshot", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("create_request_receipts")
    op.drop_index("ix_monitoring_configurations_name", table_name="monitoring_configurations")
    op.drop_table("monitoring_configurations")
