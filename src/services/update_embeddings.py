import os
import sys
import logging
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add your project's root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your project's modules
from embedding_generator import EmbeddingGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Update embeddings for resumes in the database')
    parser.add_argument('--user', type=int, help='User ID to update embeddings for (optional)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing (default: 10)')
    args = parser.parse_args()
    
    try:
        # Get database connection string from environment variable
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            logger.error("DATABASE_URL environment variable is not set")
            return 1
            
        # Create database engine and session
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Initialize embedding generator
        generator = EmbeddingGenerator()
        
        # Run the embedding update
        logger.info("Starting embedding update process...")
        stats = generator.update_all_embeddings(db, user_id=args.user, batch_size=args.batch_size)
        
        # Log results
        logger.info(f"Embedding update completed: {stats['success']} successful, {stats['failed']} failed")
        logger.info(f"Total duration: {stats['duration_seconds']:.2f} seconds")
        
        return 0
        
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    sys.exit(main())