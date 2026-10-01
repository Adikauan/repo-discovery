"""Persist scheduled occurrence identity and prevent duplicate MiningExecutions."""
from alembic import op
import sqlalchemy as sa

revision = "0007_sched_exec_idem"
down_revision = "0006_repository_executions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mining_executions", sa.Column("scheduled_occurrence_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "uq_execution_scheduled_occurrence",
        "mining_executions",
        ["monitoring_configuration_id", "scheduled_occurrence_at"],
        unique=True,
        postgresql_where=sa.text("trigger_type = 'scheduled' AND scheduled_occurrence_at IS NOT NULL"),
    )


def downgrade():
    op.drop_index("uq_execution_scheduled_occurrence", table_name="mining_executions")
    op.drop_column("mining_executions", "scheduled_occurrence_at")
