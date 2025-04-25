"""Add folders and resume models

Revision ID: 086f18a9a2f9
Revises: 
Create Date: 2025-04-25 15:01:39.059886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '086f18a9a2f9'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('mongo_id', sa.String(), nullable=False, index=True),
        sa.Column('folder_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('candidate_name', sa.String(), nullable=True),
        sa.Column('candidate_email', sa.String(), nullable=True),
        sa.Column('skills', sa.JSON(), nullable=True),
        sa.Column('education', sa.JSON(), nullable=True),
        sa.Column('experience', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('resumes')
    op.drop_table('folders')
  
