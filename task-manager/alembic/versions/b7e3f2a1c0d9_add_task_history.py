"""add task_history table

Revision ID: b7e3f2a1c0d9
Revises: a3f2c1d0e4b5
Create Date: 2026-03-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'b7e3f2a1c0d9'
down_revision: Union[str, None] = 'a3f2c1d0e4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'taskhistory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('field', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('old_value', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('new_value', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['task.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_taskhistory_task_id', 'taskhistory', ['task_id'])
    op.create_index('ix_taskhistory_changed_at', 'taskhistory', ['changed_at'])


def downgrade() -> None:
    op.drop_index('ix_taskhistory_changed_at', table_name='taskhistory')
    op.drop_index('ix_taskhistory_task_id', table_name='taskhistory')
    op.drop_table('taskhistory')
