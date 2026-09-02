"""1-minute sensor rollups for retention (updates03 P4)

At the firmware's 3 s cadence each incubator writes ~28,800 rows/day. Raw data is
kept for a window (default 7 days) and then dropped, but the shape of the history
is preserved as one row per incubator per minute.

avg AND min/max, not just avg: a one-minute mean would smooth away a ten-second
desaturation, which is precisely the event worth keeping.

Revision ID: e8c4b2f91d37
Revises: d7f3a1c85b60
Create Date: 2026-09-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e8c4b2f91d37"
down_revision: Union[str, None] = "d7f3a1c85b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_METRICS = [
    ("suhu_bayi", sa.Numeric(4, 1)),
    ("suhu_inkubator", sa.Numeric(4, 1)),
    ("kelembapan_inkubator", sa.Numeric(5, 2)),
    ("heart_rate", sa.Numeric(5, 1)),
    ("spo2", sa.Numeric(5, 2)),
]


def upgrade() -> None:
    cols = [
        sa.Column("bucket_id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("incubator_id", UUID(as_uuid=True),
                  sa.ForeignKey("incubators.incubator_id", ondelete="CASCADE"),
                  nullable=False),
        # Whoever was in the incubator during the minute. Nullable: an empty
        # incubator still records air temperature.
        sa.Column("baby_id", UUID(as_uuid=True),
                  sa.ForeignKey("babies.baby_id", ondelete="SET NULL"), nullable=True),
        sa.Column("minute", sa.DateTime(timezone=True), nullable=False),
        # How many raw samples this row stands for — a minute with 4 samples is
        # not the same evidence as one with 20.
        sa.Column("sample_count", sa.SmallInteger, nullable=False),
    ]
    for name, typ in _METRICS:
        cols.append(sa.Column(f"{name}_avg", typ, nullable=True))
        cols.append(sa.Column(f"{name}_min", typ, nullable=True))
        cols.append(sa.Column(f"{name}_max", typ, nullable=True))

    op.create_table("sensor_reading_minutes", *cols)

    # Makes the rollup idempotent: re-running over the same window updates rather
    # than duplicating, so a job that dies halfway can simply be run again.
    op.create_unique_constraint(
        "uq_sensor_minutes_incubator_minute",
        "sensor_reading_minutes",
        ["incubator_id", "minute"],
    )
    op.create_index(
        "idx_sensor_minutes_incubator_time",
        "sensor_reading_minutes",
        ["incubator_id", sa.text("minute DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_sensor_minutes_incubator_time", table_name="sensor_reading_minutes")
    op.drop_constraint("uq_sensor_minutes_incubator_minute", "sensor_reading_minutes")
    op.drop_table("sensor_reading_minutes")
