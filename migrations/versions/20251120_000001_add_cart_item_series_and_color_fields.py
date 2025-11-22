"""add cart item series and color fields

Revision ID: 20251120_000001_add_cart_item_series_and_color_fields
Revises: 20251120_000000_add_product_series_and_color_fields
Create Date: 2025-11-20 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = "20251120_000001_add_cart_item_series_and_color_fields"
down_revision = "20251120_000000_add_product_series_and_color_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add series and color fields to cartitem table
    with op.batch_alter_table("cartitem", schema=None) as batch_op:
        batch_op.add_column(sa.Column("selected_series", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("selected_color", sa.String(), nullable=True))


def downgrade() -> None:
    # Remove series and color fields from cartitem table
    with op.batch_alter_table("cartitem", schema=None) as batch_op:
        batch_op.drop_column("selected_color")
        batch_op.drop_column("selected_series")

