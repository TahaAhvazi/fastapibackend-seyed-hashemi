"""add product series and color fields

Revision ID: 20251120_000000_add_product_series_and_color_fields
Revises: 20251118_000000_remove_quantity_available_from_product
Create Date: 2025-11-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = "20251120_000000_add_product_series_and_color_fields"
down_revision = "20251118_000000_remove_quantity_available_from_product"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add series and color fields to product table
    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_series", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()))
        batch_op.add_column(sa.Column("series_inventory", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("series_numbers", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("available_colors", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("color_inventory", sa.JSON(), nullable=True))
    
    # Remove server default to avoid future implicit defaults on insert
    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.alter_column("is_series", server_default=None)


def downgrade() -> None:
    # Remove series and color fields from product table
    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.drop_column("color_inventory")
        batch_op.drop_column("available_colors")
        batch_op.drop_column("series_numbers")
        batch_op.drop_column("series_inventory")
        batch_op.drop_column("is_series")

