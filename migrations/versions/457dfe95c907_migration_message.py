"""Migration Message

Revision ID: 457dfe95c907
Revises: 511dea827871
Create Date: 2024-11-21 01:19:04.420312

"""
from typing import Sequence, Union
import sqlmodel

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '457dfe95c907'
down_revision: Union[str, None] = '511dea827871'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'activities', ['uid'])
    op.add_column('celery_beat', sa.Column('task_sig', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False))
    op.alter_column('celery_beat', 'task_name',
               existing_type=sa.VARCHAR(length=200),
               type_=sqlmodel.sql.sqltypes.AutoString(length=500),
               existing_nullable=False)
    op.create_unique_constraint(None, 'celery_beat', ['uid'])
    op.create_unique_constraint(None, 'matrix_pool', ['uid'])
    op.create_unique_constraint(None, 'matrix_users', ['uid'])
    op.create_unique_constraint(None, 'referrals', ['uid'])
    op.create_unique_constraint(None, 'token_meter', ['uid'])
    op.create_unique_constraint(None, 'user_stakings', ['uid'])
    op.create_unique_constraint(None, 'users', ['uid'])
    op.create_unique_constraint(None, 'wallets', ['uid'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'wallets', type_='unique')
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_constraint(None, 'user_stakings', type_='unique')
    op.drop_constraint(None, 'token_meter', type_='unique')
    op.drop_constraint(None, 'referrals', type_='unique')
    op.drop_constraint(None, 'matrix_users', type_='unique')
    op.drop_constraint(None, 'matrix_pool', type_='unique')
    op.drop_constraint(None, 'celery_beat', type_='unique')
    op.alter_column('celery_beat', 'task_name',
               existing_type=sqlmodel.sql.sqltypes.AutoString(length=500),
               type_=sa.VARCHAR(length=200),
               existing_nullable=False)
    op.drop_column('celery_beat', 'task_sig')
    op.drop_constraint(None, 'activities', type_='unique')
    # ### end Alembic commands ###