"""per-incubator sensor thresholds + doctor notes

Adds:
  - incubators.alert_thresholds (JSONB, nullable) — admin-set min/max bounds per
    sensor metric, consumed later by the IoT alert engine. NULL = use code defaults.
  - doctor_notes table — free-text "Catatan Dokter" written by a dokter during
    observation; shown at the end of the report + PDF.

Both are additive/nullable, so existing rows and flows keep working.

Revision ID: c9e7b2a4f610
Revises: b8e4f1c02a37
Create Date: 2026-08-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9e7b2a4f610"
down_revision: Union[str, None] = "b8e4f1c02a37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incubators",
        sa.Column("alert_thresholds", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "doctor_notes",
        sa.Column(
            "note_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "baby_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("babies.baby_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recorded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("observation_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("catatan", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_doctor_notes_baby", "doctor_notes", ["baby_id"])


def downgrade() -> None:
    op.drop_index("ix_doctor_notes_baby", table_name="doctor_notes")
    op.drop_table("doctor_notes")
    op.drop_column("incubators", "alert_thresholds")
