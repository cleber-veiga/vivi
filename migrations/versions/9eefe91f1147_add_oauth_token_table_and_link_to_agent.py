"""add oauth_token table and link to agent

Revision ID: 9eefe91f1147
Revises: 6d44f1912a4e
Create Date: 2025-08-05 20:49:10.215125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9eefe91f1147'
down_revision: Union[str, Sequence[str], None] = '6d44f1912a4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
