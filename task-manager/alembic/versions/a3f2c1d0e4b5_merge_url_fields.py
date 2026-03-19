"""merge figma_url and confluence_url into link_url

Revision ID: a3f2c1d0e4b5
Revises: 8b019987a851
Create Date: 2026-03-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'a3f2c1d0e4b5'
down_revision: Union[str, None] = '8b019987a851'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('task', sa.Column('link_url', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))

    # Migrate existing data: prefer figma_url, fall back to confluence_url
    op.execute("""
        UPDATE task
        SET link_url = CASE
            WHEN figma_url IS NOT NULL AND figma_url != '' THEN figma_url
            WHEN confluence_url IS NOT NULL AND confluence_url != '' THEN confluence_url
            ELSE NULL
        END
    """)

    op.drop_column('task', 'figma_url')
    op.drop_column('task', 'confluence_url')


def downgrade() -> None:
    op.add_column('task', sa.Column('figma_url', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))
    op.add_column('task', sa.Column('confluence_url', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))
    op.execute("UPDATE task SET figma_url = link_url WHERE link_url IS NOT NULL")
    op.drop_column('task', 'link_url')
