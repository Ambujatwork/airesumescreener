from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import BackgroundTasks
import logging
from src.models.job import Job
from src.schemas.job import JobCreate
from src.services.text_parser import TextParser
from src.services.embedding_background_manager import EmbeddingBackgroundManager

logger = logging.getLogger(__name__)

def create_job(db: Session, job: JobCreate, user_id: int, background_tasks: BackgroundTasks = None):
    try:
        parser = TextParser()
        job_metadata = parser.parse_text(job.description, parse_type="job")
        

        db_job = Job(
            title=job.title,
            description=job.description,
            role=job.role if job.role is not None else "",
            user_id=user_id,
            job_metadata=job_metadata or {}  # Ensure we don't insert None
        )
        
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        
        # Schedule background embedding generation if background_tasks is available
        if background_tasks:
            EmbeddingBackgroundManager.schedule_job_embedding_task(
                background_tasks,
                db,
                db_job.id
            )
            logger.info(f"Scheduled background embedding generation for job ID: {db_job.id}")
            
        return db_job
        
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        db.rollback()
        raise
    

def get_job_by_id(db: Session, job_id: int, user_id: int) -> Optional[Job]:
    """Get a job by ID for a specific user."""
    return db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()

def get_jobs_by_user(db: Session, user_id: int) -> List[Job]:
    """Get all jobs associated with a user."""
    return db.query(Job).filter(Job.user_id == user_id).all()

def delete_job(db: Session, job_id: int, user_id: int) -> bool:
    """Delete a job by ID for a specific user."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if job:
        db.delete(job)
        db.commit()
        return True
    return False