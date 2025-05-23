from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..dependencies.security import get_current_user
from ..schemas.job import JobCreate, Job
from ..schemas.resume import Resume
from ..crud.job import create_job, get_job_by_id, get_jobs_by_user, delete_job
from ..crud.resume import get_resumes_by_folder
from ..services.ranking_service import RankingService  
from ..models.user import User


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=Job)
def create_new_job(
    job: JobCreate,
    background_tasks: BackgroundTasks = None,  # Added background_tasks parameter
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_job(db, job, current_user.id, background_tasks)  

@router.get("/", response_model=List[Job])
def get_all_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_jobs_by_user(db, current_user.id)

@router.get("/{job_id}", response_model=Job)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = get_job_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.delete("/{job_id}")
def delete_job_endpoint(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if delete_job(db, job_id, current_user.id):
        return {"message": "Job deleted successfully"}
    raise HTTPException(status_code=404, detail="Job not found")

@router.get("/candidates/rank", response_model=List[Resume])
async def rank_candidates(
    job_id: int = Query(..., description="ID of the job to rank candidates against"),
    folder_id: Optional[int] = Query(None, description="Optional folder ID to filter resumes"),
    top_n: Optional[int] = Query(None, description="Number of top candidates to return"),
    use_embeddings: bool = Query(True, description="Whether to use embeddings for ranking"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rank candidates (resumes) against a job description.
    Can use either embedding-based semantic matching or metadata-based matching.
    """
    # Get the job
    job = get_job_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get resumes to rank
    resumes = get_resumes_by_folder(db, folder_id=folder_id, user_id=current_user.id)
    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes found")

    # Remove duplicates
    unique_resumes_dict = {resume.id: resume for resume in resumes}
    unique_resumes = list(unique_resumes_dict.values())

    # Initialize ranking service
    ranking_service = RankingService()

    # Choose ranking method based on parameter and availability of embeddings
    if use_embeddings:
        try:
            # Perform embedding-based ranking
            ranked_resumes = await ranking_service.rank_resumes_by_job_id(
                db, job_id, unique_resumes, update_embeddings=True
            )
        except Exception as e:
            # Fall back to metadata-based ranking if embedding ranking fails
            import logging
            logging.error(f"Error in embedding-based ranking: {str(e)}")
            ranked_resumes = ranking_service.rank_resumes_by_job_metadata(unique_resumes, job.description)
    else:
        # Use metadata-based ranking
        ranked_resumes = ranking_service.rank_resumes_by_job_metadata(unique_resumes, job.description)

    # Apply top_n filter if specified
    if top_n and top_n > 0:
        ranked_resumes = ranked_resumes[:top_n]

    return ranked_resumes