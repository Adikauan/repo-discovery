"""Add encrypted GitLab credentials."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_gitlab_credentials"
down_revision = "0001_monitoring_configurations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gitlab_credentials",
        sa.Column("monitoring_configuration_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("monitoring_configurations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("encrypted_token", sa.LargeBinary(), nullable=False),
        sa.Column("credential_revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_validation_result", sa.String(32), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_validation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_url_fingerprint", sa.String(64), nullable=True),
        sa.CheckConstraint("credential_revision > 0", name="ck_gitlab_credentials_revision_positive"),
        sa.CheckConstraint("last_validation_result IS NULL OR last_validation_result IN "
                           "('success','invalid_credentials','forbidden','unreachable','timeout','invalid_response','rate_limited','provider_unavailable')",
                           name="ck_gitlab_credentials_validation_result"),
    )


def downgrade():
    op.drop_table("gitlab_credentials")
