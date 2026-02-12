"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-12 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "runners",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("runner_id", sa.String(), sa.ForeignKey("runners.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("total_distance_m", sa.Float(), nullable=False, server_default="0"),
    )

    op.create_table(
        "measures",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("humidite", sa.Float(), nullable=False),
        sa.Column("pression", sa.Float(), nullable=False),
        sa.Column("batterie", sa.Float(), nullable=False),
        sa.Column("distance_m", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("measures")
    op.drop_table("sessions")
    op.drop_table("runners")
