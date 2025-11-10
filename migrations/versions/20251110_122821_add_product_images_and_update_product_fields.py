"""add product images and update product fields

Revision ID: 20251110_122821
Revises: 20251020_185320
Create Date: 2025-11-10T12:28:21.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251110_122821'
down_revision = '20251020_185320'
branch_labels = None
depends_on = None


def upgrade():
    # Create product_images table
    op.create_table(
        'product_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('image_url', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_images_id'), 'product_images', ['id'], unique=False)
    op.create_index(op.f('ix_product_images_product_id'), 'product_images', ['product_id'], unique=False)
    
    # Alter product table - make purchase_price and sale_price nullable
    op.alter_column('product', 'purchase_price',
                    existing_type=sa.Float(),
                    nullable=True)
    op.alter_column('product', 'sale_price',
                    existing_type=sa.Float(),
                    nullable=True)


def downgrade():
    # Revert product table changes
    op.alter_column('product', 'sale_price',
                    existing_type=sa.Float(),
                    nullable=False)
    op.alter_column('product', 'purchase_price',
                    existing_type=sa.Float(),
                    nullable=False)
    
    # Drop product_images table
    op.drop_index(op.f('ix_product_images_product_id'), table_name='product_images')
    op.drop_index(op.f('ix_product_images_id'), table_name='product_images')
    op.drop_table('product_images')

