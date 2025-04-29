from sqlalchemy.orm import Session
from bson import ObjectId
from src.models.resume import Resume
from src.database_mongo import resumes_collection
import json

async def create_resume(
    db: Session, 
    folder_id: int, 
    user_id: int, 
    filename: str, 
    content: bytes,
    metadata: dict = None
):
    # Store raw content in MongoDB
    mongo_result = await resumes_collection.insert_one({
        "content": content.decode("utf-8", errors="ignore"),
        "filename": filename,
        "folder_id": folder_id,
        "user_id": user_id
    })
    
    # Store metadata in PostgreSQL
    db_resume = Resume(
        filename=filename,
        folder_id=folder_id,
        user_id=user_id,
        mongo_id=str(mongo_result.inserted_id),
        candidate_name=metadata.get("personal_info", {}).get("name") if metadata else None,
        candidate_email=metadata.get("personal_info", {}).get("email") if metadata else None,
        skills=metadata.get("skills") if metadata else None, 
        education=metadata.get("education") if metadata else None,
        experience=metadata.get("experience") if metadata else None,
        parsed_metadata = metadata
    )
    
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return db_resume

async def get_resume_content(resume_id: str):
    result = await resumes_collection.find_one({"_id": ObjectId(resume_id)})
    return result["content"] if result else None

def get_resumes_by_folder(db: Session, folder_id: int, user_id: int):
    return db.query(Resume).filter(
        Resume.folder_id == folder_id,
        Resume.user_id == user_id
    ).all()