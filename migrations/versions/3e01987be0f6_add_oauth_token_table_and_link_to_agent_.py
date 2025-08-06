"""add oauth_token table and link to agent new

Revision ID: 3e01987be0f6
Revises: 9eefe91f1147
Create Date: 2025-08-05 20:50:23.653589

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e01987be0f6'
down_revision: Union[str, Sequence[str], None] = '9eefe91f1147'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
