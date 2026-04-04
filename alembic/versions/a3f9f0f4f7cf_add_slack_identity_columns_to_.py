"""add slack identity columns to integration accounts

Revision ID: a3f9f0f4f7cf
Revises: 92080696a7df
Create Date: 2026-04-05 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3f9f0f4f7cf"
down_revision: Union[str, Sequence[str], None] = "92080696a7df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("integration_accounts", sa.Column("slack_team_id", sa.String(), nullable=True))
    op.add_column("integration_accounts", sa.Column("slack_user_id", sa.String(), nullable=True))

    op.execute(
        """
        UPDATE integration_accounts
        SET
            slack_team_id = NULLIF(split_part(account_identifier, ':', 1), ''),
            slack_user_id = NULLIF(split_part(account_identifier, ':', 2), '')
        WHERE provider = 'slack'
          AND position(':' in account_identifier) > 0
        """
    )

    op.create_unique_constraint(
        "uq_integration_accounts_provider_user_slack_identity",
        "integration_accounts",
        ["provider", "user_id", "slack_team_id", "slack_user_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_integration_accounts_provider_user_slack_identity",
        "integration_accounts",
        type_="unique",
    )
    op.drop_column("integration_accounts", "slack_user_id")
    op.drop_column("integration_accounts", "slack_team_id")
