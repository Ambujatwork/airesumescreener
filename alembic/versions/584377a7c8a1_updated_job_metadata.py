"""Updated job metadata

Revision ID: 584377a7c8a1
Revises: 9d60ceb41f56
Create Date: 2025-04-29 15:41:55.802946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '584377a7c8a1'
down_revision: Union[str, None] = '9d60ceb41f56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'jobs', 'job_metadata',
        type_=postgresql.JSONB(),
        postgresql_using='job_metadata::jsonb'
    )


def downgrade() -> None:
    op.alter_column(
        'jobs', 'job_metadata',
        type_=sa.TEXT(),
        postgresql_using='job_metadata::text'  # Explicit cast to TEXT
    )
