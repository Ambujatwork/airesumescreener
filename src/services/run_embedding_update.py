#!/usr/bin/env python
"""
Script to update embeddings for all resumes in the database.
This script is meant to be run directly from the command line.

Example usage:
    python run_embedding_update.py --all
    python run_embedding_update.py --user 123
    python run_embedding_update.py --resume 456
"""

import os
import sys
import argparse
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import src.models
# Add the project root to the Python path
sys.path.append("/src")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('embedding_update.log')
    ]
)
logger = logging.getLogger(__name__)

# Import your models and the embedding generator
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.models.resume import Resume as ResumeModel
from embedding_generator import EmbeddingGenerator

def get_db_session():
    """Create and return a database session."""
    # Get database URL from environment variable
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Create engine and session
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def update_single_resume(resume_id: int, db: Session):
    """Update embedding for a single resume."""
    resume = db.query(ResumeModel).filter(ResumeModel.id == resume_id).first()
    if not resume:
        logger.error(f"Resume with ID {resume_id} not found")
        return False
    
    generator = EmbeddingGenerator()
    success = generator.update_resume_embedding(db, resume)
    
    if success:
        logger.info(f"Successfully updated embedding for resume ID {resume_id}")
    else:
        logger.error(f"Failed to update embedding for resume ID {resume_id}")
    
    return success

def update_user_resumes(user_id: int, db: Session):
    """Update embeddings for all resumes belonging to a user."""
    generator = EmbeddingGenerator()
    stats = generator.update_all_embeddings(db, user_id=user_id)
    
    logger.info(f"Updated embeddings for user {user_id}: "
                f"{stats['success']} successful, {stats['failed']} failed, "
                f"duration: {stats['duration_seconds']:.2f}s")
    
    return stats

def update_all_resumes(db: Session):
    """Update embeddings for all resumes in the database."""
    generator = EmbeddingGenerator()
    stats = generator.update_all_embeddings(db)
    
    logger.info(f"Updated all embeddings: "
                f"{stats['success']} successful, {stats['failed']} failed, "
                f"duration: {stats['duration_seconds']:.2f}s")
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Update embeddings for resumes")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true', help='Update all resumes')
    group.add_argument('--user', type=int, help='Update resumes for a specific user')
    group.add_argument('--resume', type=int, help='Update a specific resume')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    
    args = parser.parse_args()
    
    try:
        # Get database session
        db = get_db_session()
        
        start_time = time.time()
        logger.info("Starting embedding update process...")
        
        if args.all:
            update_all_resumes(db)
        elif args.user:
            update_user_resumes(args.user, db)
        elif args.resume:
            update_single_resume(args.resume, db)
        
        elapsed = time.time() - start_time
        logger.info(f"Embedding update process completed in {elapsed:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error during embedding update: {str(e)}")
        return 1
    finally:
        if 'db' in locals():
            db.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())