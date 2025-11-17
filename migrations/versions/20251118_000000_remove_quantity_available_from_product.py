"""remove quantity_available from product

Revision ID: 20251118_000000_remove_quantity_available_from_product
Revises: 20251116_001000_create_category_table
Create Date: 2025-11-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251118_000000_remove_quantity_available_from_product"
down_revision = "20251116_001000_create_category_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop quantity_available column from product table
    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.drop_column("quantity_available")


def downgrade() -> None:
    # Add quantity_available column back to product table
    with op.batch_alter_table("product", schema=None) as batch_op:
        batch_op.add_column(sa.Column("quantity_available", sa.Float(), nullable=False, server_default="0"))

