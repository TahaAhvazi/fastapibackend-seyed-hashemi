"""add extra fields to product

Revision ID: 20251116_000000_add_product_extra_fields
Revises: 20251110_132402_add_excel_data_to_customer
Create Date: 2025-11-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251116_000000_add_product_extra_fields"
down_revision = "20251110_132402"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("product") as batch_op:
        batch_op.add_column(sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()))
        batch_op.add_column(sa.Column("shrinkage", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()))
        batch_op.add_column(sa.Column("width", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("usage", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("season", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("weave_type", sa.String(), nullable=True))

    # Remove server defaults to avoid future implicit defaults on insert
    with op.batch_alter_table("product") as batch_op:
        batch_op.alter_column("is_available", server_default=None)
        batch_op.alter_column("visible", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("product") as batch_op:
        batch_op.drop_column("weave_type")
        batch_op.drop_column("season")
        batch_op.drop_column("usage")
        batch_op.drop_column("width")
        batch_op.drop_column("visible")
        batch_op.drop_column("shrinkage")
        batch_op.drop_column("is_available")


