"""outbox claimed_at for short publish transactions

Revision ID: 20250330_0002
Revises: 20250330_0001
Create Date: 2025-03-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20250330_0002"
down_revision: str | None = "20250330_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbox",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_claimed_at", "outbox", ["claimed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_outbox_claimed_at", table_name="outbox")
    op.drop_column("outbox", "claimed_at")
