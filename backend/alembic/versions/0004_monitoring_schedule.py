"""Persist versioned Monitoring Configuration schedules."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_monitoring_schedule"
down_revision = "0003_gitlab_scope"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monitoring_schedules",
        sa.Column("monitoring_configuration_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("monitoring_configurations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("configured", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("recurrence_type", sa.String(16), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("execution_time", sa.Time(timezone=False), nullable=True),
        sa.Column("timezone", sa.String(128), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_monitoring_schedules_version_positive"),
        sa.CheckConstraint(
            "(configured = false AND recurrence_type IS NULL AND enabled IS NULL AND execution_time IS NULL "
            "AND timezone IS NULL AND day_of_week IS NULL AND day_of_month IS NULL AND created_at IS NULL) OR "
            "(configured = true AND recurrence_type IS NOT NULL AND enabled IS NOT NULL AND execution_time IS NOT NULL "
            "AND timezone IS NOT NULL AND created_at IS NOT NULL)",
            name="ck_monitoring_schedules_configured_payload",
        ),
        sa.CheckConstraint(
            "(configured = false) OR "
            "(recurrence_type = 'daily' AND day_of_week IS NULL AND day_of_month IS NULL) OR "
            "(recurrence_type = 'weekly' AND day_of_week BETWEEN 1 AND 7 AND day_of_month IS NULL) OR "
            "(recurrence_type = 'monthly' AND day_of_month BETWEEN 1 AND 31 AND day_of_week IS NULL)",
            name="ck_monitoring_schedules_recurrence_fields",
        ),
        sa.CheckConstraint("recurrence_type IS NULL OR recurrence_type IN ('daily','weekly','monthly')",
                           name="ck_monitoring_schedules_recurrence_type"),
    )


def downgrade():
    op.drop_table("monitoring_schedules")
