import json  # Add this import
from sqlalchemy.orm import Session
from src.models.job import Job
from src.schemas.job import JobCreate
from src.services.text_parser import TextParser

def create_job(db: Session, job: JobCreate, user_id: int):
    parser = TextParser()
    parsed_metadata = parser.parse_text(job.description, parse_type="job")

    if not parsed_metadata:
        parsed_metadata = {"skills": {"required": [], "preferred": []}}  # Fallback structure

    # Serialize the parsed metadata to a JSON string
    db_job = Job(
        title=job.title,
        description=job.description,
        role=job.role,
        job_metadata=json.dumps(parsed_metadata),  # <-- Serialize here
        user_id=user_id
    )
    
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job_by_id(db: Session, job_id: int, user_id: int):
    return db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()