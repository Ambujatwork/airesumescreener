from fastapi import BackgroundTasks
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from src.services.embedding_manager import EmbeddingManager

logger = logging.getLogger(__name__)

class EmbeddingBackgroundManager:
    """
    Manages background tasks for embedding generation.
    This class helps decouple the embedding generation process from request handling.
    """
    
    @staticmethod
    async def process_resume_embeddings(
        db: Session,
        resume_ids: List[int],
        force_update: bool = False
    ):
        """Background task to process resume embeddings"""
        try:
            embedding_manager = EmbeddingManager()
            results = await embedding_manager.update_resume_embeddings(db, resume_ids, force_update)
            
            # Log results
            successful = [id for id, success in results.items() if success]
            failed = [id for id, success in results.items() if not success]
            
            logger.info(f"Background embedding generation completed for {len(successful)} resumes")
            if failed:
                logger.warning(f"Failed to generate embeddings for {len(failed)} resumes: {failed}")
                
        except Exception as e:
            logger.error(f"Error in background resume embedding generation: {str(e)}")
    
    @staticmethod
    async def process_job_embeddings(
        db: Session,
        job_ids: List[int]
    ):
        """Background task to process job embeddings"""
        try:
            embedding_manager = EmbeddingManager()
            results = await embedding_manager.update_job_embeddings(db, job_ids)
            
            # Log results
            successful = [id for id, success in results.items() if success]
            failed = [id for id, success in results.items() if not success]
            
            logger.info(f"Background embedding generation completed for {len(successful)} jobs")
            if failed:
                logger.warning(f"Failed to generate embeddings for {len(failed)} jobs: {failed}")
                
        except Exception as e:
            logger.error(f"Error in background job embedding generation: {str(e)}")
    
    @staticmethod
    def schedule_resume_embedding_task(
        background_tasks: BackgroundTasks,
        db: Session,
        resume_id: int
    ):
        """Schedule a background task to generate embeddings for a single resume"""
        background_tasks.add_task(
            EmbeddingBackgroundManager.process_resume_embeddings, 
            db, 
            [resume_id],
            False
        )
        logger.info(f"Scheduled background embedding generation for resume ID: {resume_id}")
    
    @staticmethod
    def schedule_job_embedding_task(
        background_tasks: BackgroundTasks,
        db: Session,
        job_id: int
    ):
        """Schedule a background task to generate embeddings for a single job"""
        background_tasks.add_task(
            EmbeddingBackgroundManager.process_job_embeddings, 
            db, 
            [job_id]
        )
        logger.info(f"Scheduled background embedding generation for job ID: {job_id}")