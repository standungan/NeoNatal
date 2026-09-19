"""user soft delete

Deleting an account must not take its records with it. Seven tables point at users.id
with ON DELETE NO ACTION - monitoring, observations, involvement, aksi, doctor notes,
and both columns of baby placements - so a row that is referenced cannot be removed
at all. Two more are SET NULL - audit_logs.user_id and sensor_alerts.acknowledged_by -
where removing it would silently erase who did something.

So an account with any of those is kept and marked deleted instead: gone from every
list, unable to sign in, never offered as a DPJP - while every record, placement and
audit entry still names its author. Its email stays taken, so one address always
means one person in the audit trail.

An account with no records at all is still removed outright; that path does not use
this column.

Revision ID: f4b7d2e9a613
Revises: e8c4b2f91d37
Create Date: 2026-09-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4b7d2e9a613"
down_revision: Union[str, None] = "e8c4b2f91d37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Downgrading resurrects deleted accounts as merely inactive: is_active was set
    # false at deletion and stays false, so nobody regains access.
    op.drop_column("users", "deleted_at")
