"""device ip provenance and optional allowlist

Coupling of incubator to device is unchanged: the authenticated path uses the
device key, and the legacy prototype path uses the payload label ("inc1"). IP is
deliberately NOT an identity here — DHCP reassigns it and anything on the LAN can
claim it. These two columns give it the jobs it is actually good for:

  last_ip     provenance — which host a reading came from, so an admin can match
              a row to a physical box and spot two rigs claiming one incubator
  allowed_ip  an optional coarse filter for the UNAUTHENTICATED legacy route,
              accepting a single address or a CIDR. Left NULL, nothing changes.

Revision ID: c2b9d4e71a58
Revises: a1f7c3d90e42
Create Date: 2026-09-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2b9d4e71a58"
down_revision: Union[str, None] = "a1f7c3d90e42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 45 chars: enough for a full IPv6 literal, and for an IPv4 CIDR.
    op.add_column("devices", sa.Column("last_ip", sa.String(length=45), nullable=True))
    op.add_column("devices", sa.Column("allowed_ip", sa.String(length=45), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "allowed_ip")
    op.drop_column("devices", "last_ip")
