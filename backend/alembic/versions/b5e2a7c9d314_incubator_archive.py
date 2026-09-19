"""incubator archive + per-baby sensor history

An incubator that has held a baby cannot be deleted: its placements are the babies'
admission records, and its sensor readings, minute buckets and alerts CASCADE with
it. So a retired incubator is archived instead - the row stays, every history that
hangs off it stays attached, and the app simply stops offering it: gone from the
dashboard, the stats and the registration picker, its number never reused.

sensor_alerts.resolved_reason: until now an alert was only ever closed by readings
coming back in range. Discharge and archive now close alerts too - a baby who has
gone home cannot recover on this incubator's probe, and an alert left open would
keep flipping the empty incubator to 'warning', which blocks the next admission.
NULL keeps its old meaning (readings recovered); the new values say who closed it,
so the history never claims a baby recovered when they were simply discharged.

The three baby_id indexes serve the new per-baby history (a discharged baby's
chart and alerts). Partial, because an empty incubator's rows carry no baby.

Revision ID: b5e2a7c9d314
Revises: f4b7d2e9a613
Create Date: 2026-09-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5e2a7c9d314"
down_revision: Union[str, None] = "f4b7d2e9a613"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("incubators", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("sensor_alerts", sa.Column("resolved_reason", sa.String(20), nullable=True))
    op.create_check_constraint(
        "ck_sensor_alerts_resolved_reason",
        "sensor_alerts",
        "resolved_reason IS NULL OR resolved_reason IN ('discharged', 'archived')",
    )

    op.create_index(
        "idx_sensor_readings_baby_time", "sensor_readings",
        ["baby_id", sa.text("recorded_at DESC")],
        postgresql_where=sa.text("baby_id IS NOT NULL"),
    )
    op.create_index(
        "idx_sensor_minutes_baby_time", "sensor_reading_minutes",
        ["baby_id", sa.text("minute DESC")],
        postgresql_where=sa.text("baby_id IS NOT NULL"),
    )
    op.create_index(
        "idx_sensor_alerts_baby_time", "sensor_alerts",
        ["baby_id", sa.text("started_at DESC")],
        postgresql_where=sa.text("baby_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_sensor_alerts_baby_time", table_name="sensor_alerts")
    op.drop_index("idx_sensor_minutes_baby_time", table_name="sensor_reading_minutes")
    op.drop_index("idx_sensor_readings_baby_time", table_name="sensor_readings")
    op.drop_constraint("ck_sensor_alerts_resolved_reason", "sensor_alerts", type_="check")
    op.drop_column("sensor_alerts", "resolved_reason")
    # Downgrading un-archives every incubator. They were set to 'tidak_tersedia' when
    # archived and stay so, so none becomes available for admission by accident.
    op.drop_column("incubators", "archived_at")
