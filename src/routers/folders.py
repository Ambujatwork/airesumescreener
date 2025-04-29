from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import traceback
from fastapi.responses import JSONResponse

from ..database import get_db
from ..models.user import User
from ..dependencies.security import get_current_user
from ..schemas.folder import FolderCreate, Folder
from ..schemas.resume import Resume
from ..crud.folder import create_folder, get_folders_by_user, get_folder, delete_folder
from ..crud.resume import create_resume, get_resumes_by_folder
from src.services.text_parser import TextParser
from src.services.text_extractor import TextExtractor


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


@router.post("/{folder_id}/upload_resumes", response_model=List[Resume])
async def upload_resumes_to_folder(
    folder_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    folder = get_folder(db, folder_id, current_user.id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    parser = TextParser()
    uploaded_resumes = []

    for file in files:
        try:
            extracted_text = await TextExtractor.extract_text(file)

            if not extracted_text:
                logger.warning(f"Empty or invalid file: {file.filename}")
                continue

            parsed_metadata = parser.parse_text(extracted_text, parse_type="resume") or {}

            candidate_name = parsed_metadata.get("personal_info", {}).get("name") or "Unknown"
            candidate_email = parsed_metadata.get("personal_info", {}).get("email") or ""

            skills = parsed_metadata.get("skills", [])
            if not skills:
                skills = parsed_metadata.get("technical_skills", []) + parsed_metadata.get("tools", [])

            file_content = await file.read()

            resume = await create_resume(
                db, folder_id, current_user.id, file.filename,
                file_content,
                {
                    "parsed_metadata": parsed_metadata,
                    "candidate_name": candidate_name,
                    "candidate_email": candidate_email,
                    "skills": skills
                    
                }
            )
            uploaded_resumes.append(resume)

        except Exception as e:
            logger.error(f"Failed to upload {file.filename}: {str(e)}")
            continue

    return uploaded_resumes


@router.get("/{folder_id}/resumes", response_model=List[Resume])
async def get_resumes_in_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    folder = get_folder(db, folder_id, current_user.id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    return get_resumes_by_folder(db, folder_id, current_user.id)
