"""Removed task_sig from CeleryBeat model

Revision ID: 098f9ca70af8
Revises: 9dad3513d24f
Create Date: 2024-11-21 15:43:32.155225

"""
from typing import Sequence, Union
import sqlmodel

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '098f9ca70af8'
down_revision: Union[str, None] = '9dad3513d24f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('wallets', sa.Column('totalReferralEarnings', sa.Numeric(scale=9), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('wallets', 'totalReferralEarnings')
    # ### end Alembic commands ###