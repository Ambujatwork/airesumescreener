# embedding_generator.py
import logging
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
from openai import AzureOpenAI
import os
from datetime import datetime

from src.models.resume import Resume as ResumeModel

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class EmbeddingGenerator:
    def __init__(self):
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY")
        )
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
        self.max_token_length = 8191  # Max tokens for embedding model
        
    def _extract_resume_text(self, resume: ResumeModel) -> str:
        """
        Extract searchable text content from a resume, focusing on skills, experience, education, and location.
        This function mirrors the one in HybridSearchService for consistency.
        """
        text_parts = []
        
        # Add candidate name and email
        if resume.candidate_name:
            text_parts.append(f"Name: {resume.candidate_name}")
        if resume.candidate_email:
            text_parts.append(f"Email: {resume.candidate_email}")
            
        # Add skills with higher weight (repeat for emphasis)
        if resume.skills and isinstance(resume.skills, list):
            skills_text = "Skills: " + ", ".join(resume.skills)
            text_parts.append(skills_text)
            text_parts.append(skills_text)  # Repeat skills for emphasis in embedding
            
        # Add education
        if resume.education and isinstance(resume.education, list):
            for edu in resume.education:
                if isinstance(edu, dict):
                    degree = edu.get("degree", "")
                    institution = edu.get("institution", "")
                    field = edu.get("field", "")
                    if degree or institution:
                        text_parts.append(f"Education: {degree} in {field} at {institution}")
                        
        # Add experience with higher weight
        if resume.experience and isinstance(resume.experience, list):
            for exp in resume.experience:
                if isinstance(exp, dict):
                    title = exp.get("title", "") or exp.get("job_title", "")
                    company = exp.get("company", "")
                    description = exp.get("description", "")
                    years = exp.get("years", "") or exp.get("duration", "")
                    
                    if title or company:
                        text_parts.append(f"Experience: {title} at {company} for {years}")
                    if description:
                        text_parts.append(f"Job Description: {description}")
                        
        # Add location if available in parsed_metadata
        if resume.parsed_metadata and isinstance(resume.parsed_metadata, dict):
            # Add location with higher weight for better location-based matching
            if "personal_info" in resume.parsed_metadata and "location" in resume.parsed_metadata["personal_info"]:
                location = resume.parsed_metadata["personal_info"]["location"]
                text_parts.append(f"Location: {location}")
                text_parts.append(f"Location: {location}")  # Repeat for emphasis
            
            # Add additional sections that might be in parsed metadata
            for key, value in resume.parsed_metadata.items():
                if key not in ["skills", "education", "experience", "personal_info"] and value:
                    if isinstance(value, list):
                        text_parts.append(f"{key.capitalize()}: {', '.join(str(v) for v in value)}")
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if sub_key != "location" and sub_value:  # Skip location as we've already added it
                                text_parts.append(f"{key.capitalize()} {sub_key.capitalize()}: {sub_value}")
                    else:
                        text_parts.append(f"{key.capitalize()}: {value}")
        
        return "\n".join(text_parts)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using Azure OpenAI's embedding model.
        Includes error handling and retries.
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Truncate text if needed to fit model's context window
                truncated_text = text[:self.max_token_length]
                
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=truncated_text
                )
                
                # Extract the embedding from the response
                embedding = response.data[0].embedding
                return embedding
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Error generating embedding (attempt {attempt+1}): {str(e)}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to generate embedding after {max_retries} attempts: {str(e)}")
                    return []
    
    def update_resume_embedding(self, db: Session, resume: ResumeModel) -> bool:
        """
        Update embedding for a single resume.
        Returns True if successful, False otherwise.
        """
        try:
            # Extract text from resume
            resume_text = self._extract_resume_text(resume)
            
            # Generate embedding
            embedding = self.generate_embedding(resume_text)
            
            if not embedding:
                logger.error(f"Failed to generate embedding for resume ID {resume.id}")
                return False
            
            # Update resume with new embedding
            resume.embedding = embedding
            resume.embedding_updated_at = datetime.now()
            
            # Commit the changes
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating embedding for resume ID {resume.id}: {str(e)}")
            db.rollback()
            return False
    
    def update_all_embeddings(self, db: Session, user_id: Optional[int] = None, batch_size: int = 10) -> Dict[str, Any]:
        """
        Update embeddings for all resumes in the database or for a specific user.
        Process in batches to avoid memory issues and allow for progress tracking.
        Returns statistics about the operation.
        """
        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "start_time": datetime.now(),
            "end_time": None,
            "duration_seconds": 0
        }
        
        try:
            # Build query
            query = db.query(ResumeModel)
            if user_id:
                query = query.filter(ResumeModel.user_id == user_id)
                
            # Get total count
            total_resumes = query.count()
            stats["total"] = total_resumes
            
            if total_resumes == 0:
                logger.info("No resumes found to update embeddings.")
                return stats
                
            logger.info(f"Starting embedding generation for {total_resumes} resumes")
            
            # Process in batches
            for offset in range(0, total_resumes, batch_size):
                batch = query.offset(offset).limit(batch_size).all()
                
                for resume in batch:
                    success = self.update_resume_embedding(db, resume)
                    if success:
                        stats["success"] += 1
                        logger.info(f"Successfully updated embedding for resume ID {resume.id} ({stats['success']}/{total_resumes})")
                    else:
                        stats["failed"] += 1
                        logger.error(f"Failed to update embedding for resume ID {resume.id}")
                
                db.commit()  # Commit after each batch
                logger.info(f"Processed {min(offset + batch_size, total_resumes)}/{total_resumes} resumes")
            
            stats["end_time"] = datetime.now()
            stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()
            
            logger.info(f"Embedding generation completed. Success: {stats['success']}, Failed: {stats['failed']}, Duration: {stats['duration_seconds']}s")
            return stats
            
        except Exception as e:
            logger.error(f"Error in update_all_embeddings: {str(e)}")
            db.rollback()
            stats["end_time"] = datetime.now()
            stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()
            return stats