"""add excel_data to customer

Revision ID: 20251110_132402
Revises: 20251110_122821
Create Date: 2025-11-10T13:24:02.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251110_132402'
down_revision = '20251110_122821'
branch_labels = None
depends_on = None


def upgrade():
    # Add excel_data column to customer table
    # SQLite doesn't have native JSON, so we use TEXT
    op.add_column('customer', sa.Column('excel_data', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('customer', 'excel_data')

