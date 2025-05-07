from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
from sqlalchemy.orm import Session
import asyncio

from src.models.resume import Resume
from src.models.job import Job
from .embedding_manager import EmbeddingManager
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class RankingService:
    """Service for ranking resumes against job descriptions"""
    
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        self.embedding_service = EmbeddingService()
    
    async def rank_resumes_by_job_id(
        self, 
        db: Session, 
        job_id: int, 
        resumes: List[Resume],
        update_embeddings: bool = True
    ) -> List[Resume]:
        """
        Rank resumes against a job by ID.
        
        Args:
            db: Database session
            job_id: ID of the job to rank against
            resumes: List of resumes to rank
            update_embeddings: Whether to update missing embeddings
            
        Returns:
            List of resumes sorted by relevance
        """
        # Get the job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job with ID {job_id} not found")
            return resumes
            
        # Generate job embedding
        job_embeddings = await self.embedding_manager.update_job_embeddings(db, [job_id])
        if job_id not in job_embeddings:
            logger.error(f"Failed to generate embedding for job {job_id}")
            return resumes
            
        job_embedding = job_embeddings[job_id]
        
        # Ensure resumes have embeddings
        if update_embeddings:
            resume_ids_without_embeddings = [
                resume.id for resume in resumes
                if resume.embedding is None or len(resume.embedding) == 0
            ]
            
            if resume_ids_without_embeddings:
                logger.info(f"Generating embeddings for {len(resume_ids_without_embeddings)} resumes")
                await self.embedding_manager.update_resume_embeddings(db, resume_ids_without_embeddings)
                
                # Refresh resume objects to get updated embeddings
                resume_ids = [resume.id for resume in resumes]
                resumes = db.query(Resume).filter(Resume.id.in_(resume_ids)).all()
        
        # Calculate similarity scores
        scored_resumes = []
        for resume in resumes:
            if resume.embedding is None or len(resume.embedding) == 0:
                logger.warning(f"Resume {resume.id} has no embedding, skipping")
                continue
                
            similarity = self.embedding_service.compute_similarity(resume.embedding, job_embedding)
            scored_resumes.append((resume, similarity))
            
        # Sort by similarity score (descending)
        scored_resumes.sort(key=lambda x: x[1], reverse=True)
        
        # Return sorted resumes
        return [resume for resume, _ in scored_resumes]

    def rank_resumes_by_job_metadata(
        self, 
        resumes: List[Resume], 
        job_description: str,
        top_skills_weight: float = 0.7,
        education_weight: float = 0.1,
        experience_weight: float = 0.2
    ) -> List[Resume]:
        """
        Legacy method to rank resumes against a job description using metadata.
        This will be replaced by embedding-based ranking in production.
        
        Args:
            resumes: List of resumes to rank
            job_description: Job description text
            
        Returns:
            List of resumes sorted by relevance
        """
        # Implementation of metadata-based ranking logic
        # This is provided for backward compatibility until embedding-based ranking is fully deployed
        scored_resumes = []
        
        for resume in resumes:
            # Calculate a simple score based on available metadata
            score = 0.0
            
            # Check for skills match
            if hasattr(resume, 'skills') and resume.skills:
                skills = resume.skills if isinstance(resume.skills, list) else []
                # Count how many skills from the resume appear in the job description
                skill_matches = sum(1 for skill in skills if skill.lower() in job_description.lower())
                if skills:
                    skill_score = min(skill_matches / len(skills), 1.0)
                    score += skill_score * top_skills_weight
            
            # Simple scoring for education and experience
            if hasattr(resume, 'education') and resume.education:
                score += education_weight
                
            if hasattr(resume, 'experience') and resume.experience:
                score += experience_weight
                
            scored_resumes.append((resume, score))
            
        # Sort by score (descending)
        scored_resumes.sort(key=lambda x: x[1], reverse=True)
        
        # Return sorted resumes
        return [resume for resume, _ in scored_resumes]