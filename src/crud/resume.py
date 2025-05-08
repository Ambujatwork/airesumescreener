from sqlalchemy.orm import Session
from bson import ObjectId
from fastapi import BackgroundTasks
import logging
import hashlib
from src.models.resume import Resume
from src.database_mongo import resumes_collection
from src.services.embedding_background_manager import EmbeddingBackgroundManager

logger = logging.getLogger(__name__)

async def create_resume(
    db: Session,
    folder_id: int,
    user_id: int,
    filename: str,
    content: bytes,
    metadata: dict = None,
    background_tasks: BackgroundTasks = None
):
    # Compute hash
    content_hash = hashlib.sha256(content).hexdigest()
    logger.info(f"Filename: {filename}, Content Hash: {content_hash}")

    # Check if resume already exists WITHIN THE SAME FOLDER
    existing_resume = db.query(Resume).filter(
        Resume.user_id == user_id,
        Resume.folder_id == folder_id,  # Check for folder_id match
        Resume.content_hash == content_hash
    ).first()

    if existing_resume:
        logger.info(f"Duplicate resume detected for hash: {content_hash} in folder_id: {folder_id}")
        return existing_resume  # Skip insert if already exists in this folder

    # Extract metadata
    personal_info = metadata.get("parsed_metadata", {}).get("personal_info", {}) if metadata else {}
    candidate_name = personal_info.get("name")
    candidate_email = personal_info.get("email")

    # Check if this content already exists in another folder (to reuse embeddings later)
    existing_resume_any_folder = db.query(Resume).filter(
        Resume.user_id == user_id,
        Resume.content_hash == content_hash
    ).first()

    # Store content in MongoDB (initially without resume_id)
    mongo_result = await resumes_collection.insert_one({
        "content": content.decode("utf-8", errors="ignore"),
        "filename": filename,
        "folder_id": folder_id,
        "user_id": user_id
    })
    mongo_id = str(mongo_result.inserted_id)

    # Create PostgreSQL entry
    db_resume = Resume(
        filename=filename,
        folder_id=folder_id,
        user_id=user_id,
        mongo_id=mongo_id,
        content_hash=content_hash,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        skills=metadata.get("skills") if metadata else None,
        education=metadata.get("education") if metadata else None,
        experience=metadata.get("experience") if metadata else None,
        parsed_metadata=metadata
    )

    # If this resume exists in another folder and has embeddings, copy them
    if existing_resume_any_folder and existing_resume_any_folder.embedding is not None:
        db_resume.embedding = existing_resume_any_folder.embedding
        db_resume.embedding_updated_at = existing_resume_any_folder.embedding_updated_at
        logger.info(f"Copied existing embedding from resume ID {existing_resume_any_folder.id}")

    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)

    await resumes_collection.update_one(
        {"_id": ObjectId(mongo_id)},
        {"$set": {"resume_id": db_resume.id}}
    )

    # Schedule background embedding generation if:
    # 1. We have background_tasks available
    # 2. We didn't copy embeddings from an existing resume
    if background_tasks and (not existing_resume_any_folder or existing_resume_any_folder.embedding is None):
        EmbeddingBackgroundManager.schedule_resume_embedding_task(
            background_tasks,
            db,
            db_resume.id
        )
        logger.info(f"Scheduled background embedding generation for resume ID: {db_resume.id}")

    return db_resume

async def get_resume_content(resume_id: str):
    result = await resumes_collection.find_one({"_id": ObjectId(resume_id)})
    return result["content"] if result else None

def get_resumes_by_folder(db: Session, folder_id: int, user_id: int):
    return db.query(Resume).filter(
        Resume.folder_id == folder_id,
        Resume.user_id == user_id
    ).all()