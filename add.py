"""create citizens table

Revision ID: create_citizens_table
Revises: 
Create Date: 2024-03-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_citizens_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'citizens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cccd', sa.String(length=12), nullable=False),
        sa.Column('ho_ten', sa.String(length=100), nullable=False),
        sa.Column('ngay_sinh', sa.DateTime(), nullable=False),
        sa.Column('gioi_tinh', sa.String(length=10), nullable=False),
        sa.Column('noi_thuong_tru', sa.String(length=200), nullable=False),
        sa.Column('noi_o_hien_tai', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citizens_cccd'), 'citizens', ['cccd'], unique=True)
    op.create_index(op.f('ix_citizens_id'), 'citizens', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_citizens_id'), table_name='citizens')
    op.drop_index(op.f('ix_citizens_cccd'), table_name='citizens')
    op.drop_table('citizens')