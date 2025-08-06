"""add oauth_token table and link to agent

Revision ID: 662feb936207
Revises: 3e01987be0f6
Create Date: 2025-08-05 20:51:26.962200
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '662feb936207'
down_revision: Union[str, Sequence[str], None] = '3e01987be0f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Cria a tabela oauth_token
    op.create_table(
        'oauth_token',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_email', sa.String(255), nullable=False, unique=True),
        sa.Column('access_token', sa.Text, nullable=False),
        sa.Column('refresh_token', sa.Text, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scope', sa.Text, nullable=True),
        sa.Column('token_type', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Adiciona a coluna oauth_token_id na tabela agent
    op.add_column('agent', sa.Column('oauth_token_id', sa.Integer, sa.ForeignKey('oauth_token.id'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove a coluna oauth_token_id da tabela agent
    op.drop_column('agent', 'oauth_token_id')

    # Remove a tabela oauth_token
    op.drop_table('oauth_token')