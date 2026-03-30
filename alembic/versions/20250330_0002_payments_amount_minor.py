"""payments amount as integer minor units (Money)

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
    op.add_column("payments", sa.Column("amount_minor", sa.BigInteger(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE payments SET amount_minor = ROUND((amount * 100)::numeric)::bigint",
        ),
    )
    op.alter_column("payments", "amount_minor", nullable=False)
    op.drop_column("payments", "amount")


def downgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("amount", sa.Numeric(18, 2), nullable=True),
    )
    op.execute(
        sa.text("UPDATE payments SET amount = (amount_minor::numeric / 100)"),
    )
    op.alter_column("payments", "amount", nullable=False)
    op.drop_column("payments", "amount_minor")
