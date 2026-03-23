"""rename_is_free_to_is_whitelisted

Revision ID: 2b26f307c79a
Revises: ce090ac9b123
Create Date: 2026-03-23 01:16:25.021994+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b26f307c79a'
down_revision: Union[str, None] = 'ce090ac9b123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('everapply_users', 'is_free', new_column_name='is_whitelisted')


def downgrade() -> None:
    op.alter_column('everapply_users', 'is_whitelisted', new_column_name='is_free')
