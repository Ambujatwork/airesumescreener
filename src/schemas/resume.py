from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime

class ResumeBase(BaseModel):
    filename: str

class ResumeCreate(ResumeBase):
    mongo_id: str
    candidate_name: Optional[str] = None

class Resume(ResumeBase):
    id: int
    folder_id: int
    user_id: int
    mongo_id: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    skills: Optional[List[str]] = None
    education: Optional[List[Dict[str, Any]]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    parsed_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True