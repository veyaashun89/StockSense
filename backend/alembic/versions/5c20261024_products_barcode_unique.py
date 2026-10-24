"""products_barcode_unique

Revision ID: 5c20261024
Revises: 4b20261024
Create Date: 2026-10-24 09:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision: str = '5c20261024'
down_revision: Union[str, Sequence[str], None] = '4b20261024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    cols = [c['name'] for c in inspector.get_columns('products')]

    # Add barcode column if missing
    if 'barcode' not in cols:
        op.add_column('products', sa.Column('barcode', sa.String(100), nullable=True))

    # Add unique index on barcode
    indexes = [idx['name'] for idx in inspector.get_indexes('products')]
    if 'uq_products_barcode' not in indexes:
        op.create_index('uq_products_barcode', 'products', ['barcode'], unique=True)

def downgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes('products')]
    if 'uq_products_barcode' in indexes:
        op.drop_index('uq_products_barcode', table_name='products')
