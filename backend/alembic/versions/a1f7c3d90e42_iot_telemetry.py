"""IoT telemetry — devices + sensor_readings

Adds the storage layer for per-incubator IoT devices (P0 of
updates03/IMPLEMENTATION_PLAN.md):

  - devices          — one sensor unit per incubator (UNIQUE incubator_id),
                       authenticated by the SHA-256 of an opaque device key.
  - sensor_readings  — high-frequency telemetry, deliberately separate from the
                       clinical monitoring_records table (which requires an
                       attesting user). Column types mirror it exactly so the
                       later vitals-form auto-fill is a straight copy.

Purely additive — nothing existing changes.

NOTE: mirrored into backend/database/schema.sql. Fresh databases are built from
that file (see docker-compose.yml → db init scripts + `alembic stamp head`), so a
migration that is not mirrored does not exist on a new install.

Revision ID: a1f7c3d90e42
Revises: c9e7b2a4f610
Create Date: 2026-08-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1f7c3d90e42"
down_revision: Union[str, None] = "c9e7b2a4f610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sensor_source = postgresql.ENUM("sensor", "simulator", name="sensor_source")
    sensor_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "devices",
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        # UNIQUE is what enforces "one device per incubator".
        sa.Column(
            "incubator_id",
            postgresql.UUID(as_uuid=True),
            # SET NULL, not CASCADE — the physical unit outlives the incubator row.
            sa.ForeignKey("incubators.incubator_id", ondelete="SET NULL"),
            unique=True,
            nullable=True,
        ),
        sa.Column("device_key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(100)),
        sa.Column("firmware_version", sa.String(20)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False
        ),
    )

    op.create_table(
        "sensor_readings",
        sa.Column(
            "reading_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            primary_key=True,
        ),
        sa.Column(
            "incubator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incubators.incubator_id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Denormalized from the active assignment at ingest; NULL for an idle unit.
        sa.Column(
            "baby_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("babies.baby_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("devices.device_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("suhu_bayi", sa.Numeric(4, 1)),
        sa.Column("suhu_inkubator", sa.Numeric(4, 1)),
        sa.Column("kelembapan_inkubator", sa.Numeric(5, 2)),
        sa.Column("heart_rate", sa.SmallInteger()),
        sa.Column("spo2", sa.Numeric(5, 2)),
        sa.Column("respiratory_rate", sa.SmallInteger()),
        sa.Column(
            "source",
            postgresql.ENUM("sensor", "simulator", name="sensor_source", create_type=False),
            server_default="sensor",
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False
        ),
    )
    op.create_index(
        "idx_sensor_readings_incubator_time",
        "sensor_readings",
        ["incubator_id", sa.text("recorded_at DESC")],
    )

    # Same updated_at trigger every other mutable table uses.
    op.execute(
        """
        CREATE TRIGGER trg_devices_updated_at
            BEFORE UPDATE ON devices
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_devices_updated_at ON devices;")
    op.drop_index("idx_sensor_readings_incubator_time", table_name="sensor_readings")
    op.drop_table("sensor_readings")
    op.drop_table("devices")
    postgresql.ENUM(name="sensor_source").drop(op.get_bind(), checkfirst=True)
