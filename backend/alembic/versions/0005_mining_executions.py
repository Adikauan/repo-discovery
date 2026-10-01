"""Persist execution history and database-backed active execution exclusion."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0005_mining_executions'
down_revision = '0004_monitoring_schedule'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('mining_executions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('monitoring_configuration_id', sa.Uuid(), sa.ForeignKey('monitoring_configurations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('trigger_type', sa.String(16), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('repository_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_repository_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_repository_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('finding_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_code', sa.String(64)), sa.Column('error_summary', sa.String(500)),
        sa.Column('snapshot', JSONB(), nullable=False),
        sa.CheckConstraint("trigger_type IN ('manual','scheduled')", name='ck_execution_trigger'),
        sa.CheckConstraint("status IN ('pending','running','completed','partially_completed','failed')", name='ck_execution_status'),
        sa.CheckConstraint('repository_count >= 0 AND successful_repository_count >= 0 AND failed_repository_count >= 0 AND finding_count >= 0', name='ck_execution_counters'),
        sa.CheckConstraint("(status = 'pending' AND started_at IS NULL AND completed_at IS NULL) OR (status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL) OR (status IN ('completed','partially_completed') AND started_at IS NOT NULL AND completed_at IS NOT NULL) OR (status = 'failed' AND completed_at IS NOT NULL)", name='ck_execution_timestamps'),
        sa.CheckConstraint('(started_at IS NULL OR started_at >= created_at) AND (completed_at IS NULL OR completed_at >= COALESCE(started_at, created_at))', name='ck_execution_time_order'),
        sa.CheckConstraint("(error_code IS NULL AND error_summary IS NULL) OR (status = 'failed' AND error_code IS NOT NULL AND error_summary IS NOT NULL)", name='ck_execution_error'))
    op.create_index('uq_execution_active_configuration', 'mining_executions', ['monitoring_configuration_id'], unique=True, postgresql_where=sa.text("status IN ('pending','running')"))
    op.create_index('ix_execution_newest', 'mining_executions', ['created_at', 'id'])
    op.create_index('ix_execution_owner_history', 'mining_executions', ['monitoring_configuration_id', 'created_at', 'id'])
    op.create_index('ix_execution_filters', 'mining_executions', ['status', 'trigger_type', 'created_at'])


def downgrade():
    op.drop_table('mining_executions')
