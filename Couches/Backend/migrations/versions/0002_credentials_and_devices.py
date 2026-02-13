"""add credentials and devices

Revision ID: 0002_credentials_and_devices
Revises: 0001_initial
Create Date: 2026-02-13 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_credentials_and_devices"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "runner_credentials",
        sa.Column("runner_id", sa.String(), sa.ForeignKey("runners.id"), primary_key=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "runner_devices",
        sa.Column("runner_id", sa.String(), sa.ForeignKey("runners.id"), primary_key=True),
        sa.Column("gps_ipv6", sa.String(), nullable=False),
        sa.Column("batterie_ipv6", sa.String(), nullable=False),
        sa.Column("temperature_ipv6", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("runner_devices")
    op.drop_table("runner_credentials")
