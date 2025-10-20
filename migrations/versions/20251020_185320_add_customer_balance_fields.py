"""add customer balance fields

Revision ID: 20251020_185320
Revises: 
Create Date: 2025-10-20T18:53:20.865178

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20251020_185320'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add balance fields to customer table
    op.add_column('customer', sa.Column('current_balance', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('customer', sa.Column('balance_notes', sa.Text(), nullable=True))

def downgrade():
    # Remove balance fields from customer table
    op.drop_column('customer', 'balance_notes')
    op.drop_column('customer', 'current_balance')

