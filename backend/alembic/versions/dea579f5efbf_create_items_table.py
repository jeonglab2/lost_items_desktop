"""create items table

Revision ID: dea579f5efbf
Revises: a7c56db0f0be
Create Date: 2025-07-02 17:50:33.809154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dea579f5efbf'
down_revision: Union[str, Sequence[str], None] = 'a7c56db0f0be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('items', sa.Column('found_datetime', sa.String(), nullable=False, comment='拾得日時（TIMESTAMP WITH TIME ZONE）'))
    op.add_column('items', sa.Column('accepted_datetime', sa.String(), nullable=False, comment='受付日時（TIMESTAMP WITH TIME ZONE）'))
    op.add_column('items', sa.Column('found_place', sa.String(length=255), nullable=False, comment='拾得場所'))
    op.add_column('items', sa.Column('name', sa.String(length=255), nullable=False, comment='品名'))
    op.add_column('items', sa.Column('features', sa.String(), nullable=False, comment='特徴'))
    op.add_column('items', sa.Column('color', sa.String(length=50), nullable=False, comment='色'))
    op.add_column('items', sa.Column('status', sa.String(length=50), nullable=False, comment='状態（保管中、返還済、警察届出済、廃棄済）'))
    op.add_column('items', sa.Column('storage_location', sa.String(length=255), nullable=False, comment='保管場所'))
    op.add_column('items', sa.Column('image_url', sa.String(length=255), nullable=False, comment='画像ファイルのURL'))
    op.add_column('items', sa.Column('finder_type', sa.String(length=50), nullable=False, comment='拾得者の属性（第三者、施設占有者）'))
    op.add_column('items', sa.Column('created_at', sa.String(), nullable=False, comment='作成日時（TIMESTAMP WITH TIME ZONE）'))
    op.add_column('items', sa.Column('updated_at', sa.String(), nullable=False, comment='更新日時（TIMESTAMP WITH TIME ZONE）'))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('items', 'updated_at')
    op.drop_column('items', 'created_at')
    op.drop_column('items', 'finder_type')
    op.drop_column('items', 'image_url')
    op.drop_column('items', 'storage_location')
    op.drop_column('items', 'status')
    op.drop_column('items', 'color')
    op.drop_column('items', 'features')
    op.drop_column('items', 'name')
    op.drop_column('items', 'found_place')
    op.drop_column('items', 'accepted_datetime')
    op.drop_column('items', 'found_datetime')
    # ### end Alembic commands ###
