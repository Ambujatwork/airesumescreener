from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..dependencies.security import get_current_user
from ..schemas.job import JobCreate, Job
from ..schemas.resume import Resume
from ..crud.job import create_job, get_job_by_id
from ..crud.resume import get_resumes_by_folder
from ..services.ranking_service import rank_resumes_by_job_metadata
from ..models.user import User


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=Job)
def create_new_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    
    return create_job(db, job, current_user.id)

@router.get("/rank_candidates", response_model=List[Resume])
def rank_candidates(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = get_job_by_id(db, job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Fetch resumes and rank them based on job metadata
    resumes = get_resumes_by_folder(db, folder_id=None, user_id=current_user.id)  # Adjust logic as needed
    ranked_resumes = rank_resumes_by_job_metadata(resumes, job.metadata)  # Implement ranking logic
    return ranked_resumes