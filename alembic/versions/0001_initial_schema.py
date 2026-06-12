"""Initial database schema for Pig Pesitos.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2025-05-01 00:00:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expense",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("concept", sa.String(length=15), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
    )
    op.create_unique_constraint(
        "uq_expense_user_created_at", "expense", ["user_id", "created_at"]
    )

    op.create_table(
        "monthly_limit",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column("limit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint("limit_amount > 0", name="ck_monthly_limit_amount_positive"),
    )

    op.create_index(
        "idx_expense_user_created_at",
        "expense",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_expense_user_category_created_at",
        "expense",
        ["user_id", "category", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_expense_user_category_created_at", table_name="expense")
    op.drop_index("idx_expense_user_created_at", table_name="expense")
    op.drop_table("monthly_limit")
    op.drop_constraint("uq_expense_user_created_at", "expense", type_="unique")
    op.drop_table("expense")
