"""merge channel_id and slack_identity heads

Revision ID: a4625ae3c7da
Revises: 62c38721857d, a3f9f0f4f7cf
Create Date: 2026-04-05 04:37:38.640845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4625ae3c7da'
down_revision: Union[str, Sequence[str], None] = ('62c38721857d', 'a3f9f0f4f7cf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
