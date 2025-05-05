from sqlalchemy import Column, Float, ARRAY
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '28b2a9c14ed0'
down_revision = '584377a7c8a1'  
depends_on = None

def upgrade():
    # Add embedding column to resumes table
    op.add_column('resumes', sa.Column('embedding', sa.ARRAY(sa.Float()), nullable=True))
    
    # Add embedding_updated_at to track when embeddings were last updated
    op.add_column('resumes', sa.Column('embedding_updated_at', sa.DateTime(), nullable=True))
    
    # Create an index to speed up vector similarity search
    # Note: This uses PostgreSQL's gin index which works well with array data
    op.create_index('ix_resumes_embedding', 'resumes', ['embedding'], 
                   postgresql_using='gin')
    
    # Optional: If you're using PostgreSQL and want to enable vector operations
    # You might need to install the pgvector extension
    # op.execute('CREATE EXTENSION IF NOT EXISTS vector;')

def downgrade():
    # Remove the index
    op.drop_index('ix_resumes_embedding', table_name='resumes')
    
    # Remove the embedding columns
    op.drop_column('resumes', 'embedding_updated_at')
    op.drop_column('resumes', 'embedding')