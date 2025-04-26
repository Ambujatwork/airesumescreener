from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobBase(BaseModel):
    title: str
    description: str
    role: str

class JobCreate(JobBase):
    pass

class Job(JobBase):
    id: int
    user_id: int
    job_metadata: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
