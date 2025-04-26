from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from ..database import get_db
from ..models.user import User
from ..dependencies.security import get_current_user
from ..schemas.folder import FolderCreate, Folder
from ..schemas.resume import Resume
from ..crud.folder import create_folder, get_folders_by_user, get_folder, delete_folder
from ..crud.resume import create_resume, get_resumes_by_folder
from src.services.text_parser import TextParser


import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/folders",
    tags=["Folders"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=Folder)
async def create_new_folder(
    folder: FolderCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return create_folder(db, folder, current_user.id)

@router.get("/", response_model=List[Folder])
async def get_user_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_folders_by_user(db, current_user.id)

@router.get("/{folder_id}", response_model=Folder)
async def get_folder_by_id(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    folder = get_folder(db, folder_id, current_user.id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder

@router.delete("/{folder_id}")
async def delete_folder_by_id(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = delete_folder(db, folder_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"message": "Folder deleted successfully"}

@router.post("/{folder_id}/upload_resume", response_model=Resume)
async def upload_resume_to_folder(
    folder_id: int,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify folder exists and belongs to user
    folder = get_folder(db, folder_id, current_user.id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Read file content
    try:
        content = await file.read()
        content_text = content.decode("utf-8", errors="replace")  # More robust decoding
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    # Parse resume content using TextParser
    try:
        parser = TextParser()  # Use the singleton instance
        parsed_metadata = parser.parse_text(content_text, parse_type="resume")
        
        if not parsed_metadata:
            # Fallback to empty structure if parsing fails
            parsed_metadata = {
                "personal_info": {},
                "skills": {"technical": [], "soft": []},
                "experience": [],
                "education": []
            }
    except Exception as e:
        # Log the error but continue with empty metadata
        logger.error(f"Resume parsing error: {str(e)}")
        parsed_metadata = {
            "personal_info": {},
            "skills": {"technical": [], "soft": []},
            "experience": [],
            "education": []
        }

    # Create resume
    resume = await create_resume(
        db,
        folder_id,
        current_user.id,
        file.filename,
        content,
        parsed_metadata
    )

    return resume

@router.get("/{folder_id}/resumes", response_model=List[Resume])
async def get_resumes_in_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify folder exists and belongs to user
    folder = get_folder(db, folder_id, current_user.id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    return get_resumes_by_folder(db, folder_id, current_user.id)