"""add_ats_resume_fields

Revision ID: c1a2b3d4e5f6
Revises: b805f85120b2
Create Date: 2026-03-19 00:01:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = 'b805f85120b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('everapply_users', sa.Column('total_ats_resumes_generated', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('everapply_jobmatches', sa.Column('ats_resume_url', sa.String(), nullable=True))
    op.add_column('everapply_jobmatches', sa.Column('ats_resume_generated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('everapply_jobmatches', 'ats_resume_generated_at')
    op.drop_column('everapply_jobmatches', 'ats_resume_url')
    op.drop_column('everapply_users', 'total_ats_resumes_generated')
