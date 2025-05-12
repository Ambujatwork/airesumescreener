from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
from sqlalchemy.orm import Session
import asyncio
import traceback

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
        try:
            # Get the job
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.error(f"Job with ID {job_id} not found")
                return resumes

            # Generate job embedding
            if job.embedding is None or job.embedding_updated_at is None:
                logger.info(f"Job {job_id} is missing embedding or timestamp. Generating embedding.")
                job_embeddings = await self.embedding_manager.update_job_embeddings(db, [job_id])
                logger.debug(f"Job embeddings: {job_embeddings}")
                job_embedding = job_embeddings.get(job_id)
                if job_embedding is None:
                    logger.error(f"Failed to generate embedding for job {job_id}")
                    return resumes
            else:
                logger.info(f"Using existing embedding for job {job_id}")
                job_embedding = job.embedding

            # Log embedding type and shape for debugging
            logger.debug(f"Job embedding type: {type(job_embedding)}")
            if isinstance(job_embedding, np.ndarray):
                logger.debug(f"Job embedding shape: {job_embedding.shape}")
            elif isinstance(job_embedding, list):
                logger.debug(f"Job embedding length: {len(job_embedding)}")
            
            # Ensure it's a numpy array
            if not isinstance(job_embedding, np.ndarray):
                try:
                    job_embedding = np.array(job_embedding, dtype=np.float32)
                    logger.debug(f"Converted job embedding to numpy array, shape: {job_embedding.shape}")
                except Exception as e:
                    logger.error(f"Failed to convert job embedding to numpy array: {str(e)}")
                    return resumes

            # Ensure resumes have embeddings
            if update_embeddings:
                resume_ids_without_embeddings = []
                for resume in resumes:
                    # Explicit check for missing embeddings
                    if resume.embedding is None:
                        resume_ids_without_embeddings.append(resume.id)
                    elif isinstance(resume.embedding, list) and len(resume.embedding) == 0:
                        resume_ids_without_embeddings.append(resume.id)

                if resume_ids_without_embeddings:
                    logger.info(f"Generating embeddings for {len(resume_ids_without_embeddings)} resumes")
                    await self.embedding_manager.update_resume_embeddings(db, resume_ids_without_embeddings)

                    # Refresh resume objects to get updated embeddings
                    resume_ids = [resume.id for resume in resumes]
                    resumes = db.query(Resume).filter(Resume.id.in_(resume_ids)).all()

            # Calculate similarity scores
            scored_resumes = []
            for resume in resumes:
                try:
                    # Skip resumes without embeddings
                    if resume.embedding is None:
                        logger.warning(f"Resume {resume.id} has no embedding, skipping")
                        continue
                        
                    if isinstance(resume.embedding, list) and len(resume.embedding) == 0:
                        logger.warning(f"Resume {resume.id} has empty embedding, skipping")
                        continue

                    # Debug log resume embedding
                    logger.debug(f"Resume {resume.id} embedding type: {type(resume.embedding)}")
                    
                    # Convert resume embedding to numpy array
                    resume_embedding = None
                    try:
                        resume_embedding = np.array(resume.embedding, dtype=np.float32)
                        logger.debug(f"Resume {resume.id} embedding shape: {resume_embedding.shape}")
                    except Exception as e:
                        logger.error(f"Failed to convert resume {resume.id} embedding to numpy array: {str(e)}")
                        continue
                    
                    # Calculate similarity
                    similarity = self.embedding_service.compute_similarity(resume_embedding, job_embedding)
                    logger.debug(f"Resume {resume.id} similarity: {similarity}")
                     
                    logger.info(f"Ranked resume {resume.id} with similarity {similarity}")

                    scored_resumes.append((resume, similarity))
                    
                except Exception as e:
                    logger.error(f"Error processing resume {resume.id}: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue

            # Sort by similarity score (descending)
            scored_resumes.sort(key=lambda x: x[1], reverse=True)

            # Return sorted resumes
            return [resume for resume, _ in scored_resumes]
            
        except Exception as e:
            logger.error(f"Error in embedding-based ranking: {str(e)}")
            logger.error(traceback.format_exc())
            return resumes  # Return original resumes on error

    def rank_resumes_by_job_metadata(
        self, 
        resumes: List[Resume], 
        job_description: str,
        top_skills_weight: float = 0.7,
        education_weight: float = 0.1,
        experience_weight: float = 0.2
    ) -> List[Resume]:
        
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
                if len(skills) > 0:  # Explicit check to avoid division by zero
                    skill_score = min(skill_matches / len(skills), 1.0)
                    score += skill_score * top_skills_weight
            
            if hasattr(resume, 'education') and resume.education:
                score += education_weight
                
            if hasattr(resume, 'experience') and resume.experience:
                score += experience_weight
                
            scored_resumes.append((resume, score))
            
        # Sort by score (descending)
        scored_resumes.sort(key=lambda x: x[1], reverse=True)
        
        return [resume for resume, _ in scored_resumes]
