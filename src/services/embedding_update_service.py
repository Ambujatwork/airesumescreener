from typing import List, Optional
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.resume import Resume as ResumeModel
from src.services.hybrid_search_service import HybridSearchService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class EmbeddingUpdateService:
    """Service to manage embedding updates for resumes"""
    
    def __init__(self):
        self.search_service = HybridSearchService()
        self.embedding_freshness_days = 30  # Consider embeddings stale after 30 days
    
    def update_resume_embedding(self, db: Session, resume_id: int) -> bool:
        """Update the embedding for a single resume"""
        try:
            # Get the resume
            resume = db.query(ResumeModel).filter(ResumeModel.id == resume_id).first()
            if not resume:
                logger.error(f"Resume with ID {resume_id} not found")
                return False
                
            # Extract text from resume
            resume_text = self.search_service._extract_resume_text(resume)
            
            # Generate embedding
            embedding = self.search_service._get_embedding(resume_text)
            if not embedding:
                logger.error(f"Failed to generate embedding for resume {resume_id}")
                return False
                
            # Update resume with embedding
            resume.embedding = embedding
            resume.embedding_updated_at = datetime.utcnow()
            
            # Commit to database
            db.commit()
            logger.info(f"Updated embedding for resume {resume_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating embedding for resume {resume_id}: {str(e)}")
            return False
    
    def update_stale_embeddings(self, db: Session, user_id: Optional[int] = None, 
                                folder_id: Optional[int] = None, limit: int = 100) -> int:
        """
        Update embeddings for resumes with stale or missing embeddings.
        
        Args:
            db (Session): Database session
            user_id (Optional[int]): Filter by user ID
            folder_id (Optional[int]): Filter by folder ID
            limit (int): Maximum number of resumes to update
            
        Returns:
            int: Number of resumes updated
        """
        try:
            # Calculate cutoff date for stale embeddings
            stale_cutoff = datetime.utcnow() - timedelta(days=self.embedding_freshness_days)
            
            # Build query for resumes with missing or stale embeddings
            query = db.query(ResumeModel).filter(
                (ResumeModel.embedding.is_(None)) |  # Missing embedding
                (ResumeModel.embedding_updated_at < stale_cutoff)  # Stale embedding
            )
            
            # Apply filters
            if user_id:
                query = query.filter(ResumeModel.user_id == user_id)
            if folder_id:
                query = query.filter(ResumeModel.folder_id == folder_id)
                
            # Limit query and execute
            resumes = query.limit(limit).all()
            
            # Update embeddings
            updated_count = 0
            for resume in resumes:
                if self.update_resume_embedding(db, resume.id):
                    updated_count += 1
                    
            logger.info(f"Updated embeddings for {updated_count} resumes")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating stale embeddings: {str(e)}")
            return 0