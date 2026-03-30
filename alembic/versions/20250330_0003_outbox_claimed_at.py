"""outbox claimed_at for short publish transactions

Revision ID: 20250330_0003
Revises: 20250330_0002
Create Date: 2025-03-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20250330_0003"
down_revision: str | None = "20250330_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotent: DBs that already applied the old duplicate revision may have this column.
    op.execute(
        sa.text(
            "ALTER TABLE outbox ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ",
        ),
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_outbox_claimed_at ON outbox (claimed_at)",
        ),
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_outbox_claimed_at"))
    op.execute(sa.text("ALTER TABLE outbox DROP COLUMN IF EXISTS claimed_at"))
