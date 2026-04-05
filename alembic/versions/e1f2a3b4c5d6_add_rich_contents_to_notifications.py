"""add rich_contents to notifications

Revision ID: e1f2a3b4c5d6
Revises: a4625ae3c7da
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'a4625ae3c7da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS rich_contents TEXT")


def downgrade() -> None:
    op.drop_column('notifications', 'rich_contents')
