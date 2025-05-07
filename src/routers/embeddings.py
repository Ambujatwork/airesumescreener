from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import asyncio

from ..database import get_db
from ..dependencies.security import get_current_user
from ..models.user import User
from ..models.resume import Resume
from ..models.job import Job
from ..crud.resume import get_resumes_by_folder
from ..schemas.job import Job as JobSchema
from ..schemas.resume import Resume as ResumeSchema
from ..services.embedding_manager import EmbeddingManager

router = APIRouter(
    prefix="/embeddings",
    tags=["Embeddings"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/resumes/generate", response_model=Dict[str, Any])
async def generate_resume_embeddings(
    resume_ids: Optional[List[int]] = None,
    folder_id: Optional[int] = None,
    force_update: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate or update embeddings for resumes.
    Can either provide specific resume IDs or a folder ID to process all resumes in the folder.
    """
    embedding_manager = EmbeddingManager()
    
    # If folder_id is provided, get all resumes in the folder
    if folder_id is not None:
        folder_resumes = get_resumes_by_folder(db, folder_id, current_user.id)
        if not folder_resumes:
            raise HTTPException(status_code=404, detail="No resumes found in folder")
        
        resume_ids = [resume.id for resume in folder_resumes]
    
    # Validate that we have resume IDs to process
    if not resume_ids:
        raise HTTPException(status_code=400, detail="No resume IDs provided")
    
    # Check if resumes belong to current user
    user_resumes = db.query(Resume).filter(
        Resume.id.in_(resume_ids),
        Resume.user_id == current_user.id
    ).all()
    
    found_ids = [resume.id for resume in user_resumes]
    if not found_ids:
        raise HTTPException(status_code=404, detail="No valid resumes found")
    
    # If some provided IDs don't belong to the user, filter them out
    invalid_ids = set(resume_ids) - set(found_ids)
    resume_ids = found_ids
    
    if background_tasks:
        # Process in background
        background_tasks.add_task(
            embedding_manager.update_resume_embeddings,
            db, resume_ids, force_update
        )
        return {
            "message": f"Embedding generation for {len(resume_ids)} resumes started in background",
            "resume_ids": resume_ids,
            "invalid_ids": list(invalid_ids)
        }
    else:
        # Process immediately (may take time for large batches)
        results = await embedding_manager.update_resume_embeddings(db, resume_ids, force_update)
        
        successful = [id for id, success in results.items() if success]
        failed = [id for id, success in results.items() if not success]
        
        return {
            "message": f"Embedding generation completed for {len(successful)} resumes",
            "successful": successful,
            "failed": failed,
            "invalid_ids": list(invalid_ids)
        }

@router.post("/jobs/generate", response_model=Dict[str, Any])
async def generate_job_embeddings(
    job_ids: Optional[List[int]] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate embeddings for job descriptions.
    If no job IDs are provided, process all jobs for the current user.
    """
    embedding_manager = EmbeddingManager()
    
    # If no job IDs provided, get all jobs for the user
    if not job_ids:
        user_jobs = db.query(Job).filter(Job.user_id == current_user.id).all()
        job_ids = [job.id for job in user_jobs]
    
    if not job_ids:
        raise HTTPException(status_code=404, detail="No jobs found")
    
    # Check if jobs belong to current user
    user_jobs = db.query(Job).filter(
        Job.id.in_(job_ids),
        Job.user_id == current_user.id
    ).all()
    
    found_ids = [job.id for job in user_jobs]
    if not found_ids:
        raise HTTPException(status_code=404, detail="No valid jobs found")
    
    # If some provided IDs don't belong to the user, filter them out
    invalid_ids = set(job_ids) - set(found_ids)
    job_ids = found_ids
    
    if background_tasks:
        # Process in background
        background_tasks.add_task(
            embedding_manager.update_job_embeddings,
            db, job_ids
        )
        return {
            "message": f"Embedding generation for {len(job_ids)} jobs started in background",
            "job_ids": job_ids,
            "invalid_ids": list(invalid_ids)
        }
    else:
        # Process immediately
        job_embeddings = await embedding_manager.update_job_embeddings(db, job_ids)
        
        successful = [id for id in job_embeddings.keys()]
        failed = [id for id in job_ids if id not in job_embeddings]
        
        return {
            "message": f"Embedding generation completed for {len(successful)} jobs",
            "successful": successful,
            "failed": failed,
            "invalid_ids": list(invalid_ids)
        }

@router.post("/rank")
async def rank_resumes_against_job(
    job_id: int,
    resume_ids: Optional[List[int]] = None,
    folder_id: Optional[int] = None,
    top_n: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rank resumes against a job using embeddings.
    Can provide specific resume IDs or a folder ID.
    """
    from ..services.ranking_service import RankingService
    
    # Validate job belongs to user
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get resumes to rank
    resumes = []
    if folder_id is not None:
        resumes = get_resumes_by_folder(db, folder_id, current_user.id)
    elif resume_ids:
        resumes = db.query(Resume).filter(
            Resume.id.in_(resume_ids),
            Resume.user_id == current_user.id
        ).all()
    
    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes found")
    
    # Rank resumes
    ranking_service = RankingService()
    ranked_resumes = await ranking_service.rank_resumes_by_job_id(db, job_id, resumes)
    
    # Apply top_n limit if specified
    if top_n and top_n > 0:
        ranked_resumes = ranked_resumes[:top_n]
    
    # Return ranked resume IDs with scores
    return {
        "job_id": job_id,
        "ranked_resumes": [
            {
                "id": resume.id,
                "filename": resume.filename,
                "candidate_name": resume.candidate_name or "Unknown",
                "candidate_email": resume.candidate_email,
                "skills": resume.skills
            } for resume in ranked_resumes
        ]
    }