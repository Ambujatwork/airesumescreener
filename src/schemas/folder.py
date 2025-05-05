from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FolderBase(BaseModel):
    name: str
    description: Optional[str] = None

class FolderCreate(FolderBase):
    pass

class Folder(FolderBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
