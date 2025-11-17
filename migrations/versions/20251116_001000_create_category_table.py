"""create category table

Revision ID: 20251116_001000_create_category_table
Revises: 20251116_000000_add_product_extra_fields
Create Date: 2025-11-16 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251116_001000_create_category_table"
down_revision = "20251116_000000_add_product_extra_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_category_id"), "category", ["id"], unique=False)
    op.create_index(op.f("ix_category_name"), "category", ["name"], unique=True)

    # Remove server default on visible after creation
    with op.batch_alter_table("category") as batch_op:
        batch_op.alter_column("visible", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_category_name"), table_name="category")
    op.drop_index(op.f("ix_category_id"), table_name="category")
    op.drop_table("category")


