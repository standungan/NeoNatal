"""sensor alerts (updates03 P4)

One open row per (incubator, alert_type) while a breach persists; resolved_at is
set on recovery. Only alert types a real sensor can raise exist here — apnea,
door_open and environment need hardware that does not exist, and a type nothing
can ever emit is dead schema.

Revision ID: d7f3a1c85b60
Revises: c2b9d4e71a58
Create Date: 2026-09-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

revision: str = "d7f3a1c85b60"
down_revision: Union[str, None] = "c2b9d4e71a58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # checkfirst + create_type=False on the columns, matching a1f7c3d90e42:
    # sa.Enum would try to create the type a second time inside create_table.
    alert_type = postgresql.ENUM(
        "desaturation", "bradycardia", "tachycardia", "temp_out_of_range",
        name="sensor_alert_type",
    )
    alert_type.create(op.get_bind(), checkfirst=True)
    severity = postgresql.ENUM("warning", "critical", name="sensor_alert_severity")
    severity.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "sensor_alerts",
        sa.Column("alert_id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("incubator_id", UUID(as_uuid=True),
                  sa.ForeignKey("incubators.incubator_id", ondelete="CASCADE"),
                  nullable=False),
        # Denormalised at open time: which baby was in the incubator when this
        # fired. Nullable because an empty incubator can still alert on air temp.
        sa.Column("baby_id", UUID(as_uuid=True),
                  sa.ForeignKey("babies.baby_id", ondelete="SET NULL"), nullable=True),
        sa.Column("alert_type",
                  postgresql.ENUM("desaturation", "bradycardia", "tachycardia",
                                  "temp_out_of_range", name="sensor_alert_type",
                                  create_type=False),
                  nullable=False),
        sa.Column("metric_key", sa.String(40), nullable=False),
        sa.Column("severity",
                  postgresql.ENUM("warning", "critical", name="sensor_alert_severity",
                                  create_type=False),
                  nullable=False, server_default="warning"),
        # The reading that opened it, and the bound it crossed — so the alert is
        # readable months later without re-deriving thresholds that may have changed.
        sa.Column("value", sa.Numeric(6, 2), nullable=True),
        sa.Column("threshold", sa.Numeric(6, 2), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )

    # The alert feed: newest first for one incubator.
    op.create_index("idx_sensor_alerts_incubator_time", "sensor_alerts",
                    ["incubator_id", sa.text("started_at DESC")])

    # At most ONE open alert per incubator per type. This is what makes the
    # engine idempotent: a breach that persists for a minute refreshes one row
    # instead of opening twenty.
    op.execute(
        "CREATE UNIQUE INDEX idx_sensor_alerts_open_unique "
        "ON sensor_alerts (incubator_id, alert_type) WHERE resolved_at IS NULL"
    )


def downgrade() -> None:
    op.drop_index("idx_sensor_alerts_open_unique", table_name="sensor_alerts")
    op.drop_index("idx_sensor_alerts_incubator_time", table_name="sensor_alerts")
    op.drop_table("sensor_alerts")
    postgresql.ENUM(name="sensor_alert_severity").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="sensor_alert_type").drop(op.get_bind(), checkfirst=True)
