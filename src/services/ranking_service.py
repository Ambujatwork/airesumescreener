from typing import List, Dict, Any, Optional
import json
import logging
from sqlalchemy.orm import Session
from src.schemas.resume import Resume
from src.models.resume import Resume as ResumeModel
from src.models.job import Job as JobModel
from src.services.text_parser import TextParser

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def extract_skills_from_resume(resume: Resume) -> List[str]:
    """Extract all skills from a resume."""
    skills = []
    
    try:
        if not resume.metadata:
            return []
            
        # Parse the metadata if it's a string
        metadata = resume.metadata
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                return []
        
        # First check if skills are directly available in resume object
        if hasattr(resume, 'skills') and isinstance(resume.skills, list):
            return [s.lower() for s in resume.skills if isinstance(s, str)]
        
        # Extract from metadata
        if isinstance(metadata, dict):
            # Extract from skills key (direct list)
            if "skills" in metadata and isinstance(metadata["skills"], list):
                skills.extend([s.lower() for s in metadata["skills"] if isinstance(s, str)])
            
            # Extract from structured skills object
            elif "skills" in metadata and isinstance(metadata["skills"], dict):
                # Extract technical skills
                if "technical" in metadata["skills"] and isinstance(metadata["skills"]["technical"], list):
                    skills.extend([s.lower() for s in metadata["skills"]["technical"] if isinstance(s, str)])
                
                # Extract soft skills
                if "soft" in metadata["skills"] and isinstance(metadata["skills"]["soft"], list):
                    skills.extend([s.lower() for s in metadata["skills"]["soft"] if isinstance(s, str)])
                
            # Extract from parsed_metadata if available
            if "parsed_metadata" in metadata and isinstance(metadata["parsed_metadata"], dict):
                parsed_skills = metadata["parsed_metadata"].get("skills", [])
                if isinstance(parsed_skills, list):
                    skills.extend([s.lower() for s in parsed_skills if isinstance(s, str)])
                
    except Exception as e:
        logger.error(f"Error extracting skills from resume: {str(e)}")
    
    # Remove duplicates and return
    return list(set(skills))

def extract_skills_from_job(job_metadata: Any) -> List[str]:
    """Extract required skills from job metadata."""
    required_skills = []
    
    try:
        if not job_metadata:
            return []
            
        # Parse the metadata if it's a string
        metadata = job_metadata
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                # If not valid JSON, treat as plain text
                words = metadata.lower().split()
                return [w for w in words if len(w) > 3]
        
        # Extract from structured metadata
        if isinstance(metadata, dict):
            # Extract directly from skills key
            if "skills" in metadata:
                if isinstance(metadata["skills"], dict):
                    # Get required skills from dictionary
                    if "required" in metadata["skills"] and isinstance(metadata["skills"]["required"], list):
                        required_skills.extend([s.lower() for s in metadata["skills"]["required"] if isinstance(s, str)])
                elif isinstance(metadata["skills"], list):
                    # Get skills from list
                    required_skills.extend([s.lower() for s in metadata["skills"] if isinstance(s, str)])
                    
    except Exception as e:
        logger.error(f"Error extracting skills from job: {str(e)}")
    
    # Remove duplicates and return
    return list(set([s for s in required_skills if s]))

def rank_resumes_by_job_metadata(resumes: List[Resume], job_description: str) -> List[Resume]:
    """Rank resumes based on matching with job description."""
    parser = TextParser()

    # Parse the job description to extract required skills
    job_metadata = parser.parse_text(job_description, parse_type="job")
    job_skills = []
    
    # Extract skills from the job metadata
    if job_metadata and isinstance(job_metadata, dict) and "skills" in job_metadata:
        if isinstance(job_metadata["skills"], dict) and "required" in job_metadata["skills"]:
            job_skills = job_metadata["skills"]["required"]
        elif isinstance(job_metadata["skills"], list):
            job_skills = job_metadata["skills"]
    
    if not job_skills:
        logger.warning("No job skills found in parsed metadata. Using keywords from description.")
        # Fallback to extract important keywords from description
        job_skills = [word.lower() for word in job_description.split() 
                     if len(word) > 4 and word.lower() not in 
                     ['about', 'the', 'this', 'that', 'these', 'those', 'with', 'from']]

    # Score each resume
    scored_resumes = []
    for resume in resumes:
        # Extract skills from the resume
        resume_skills = []
        if hasattr(resume, 'skills') and resume.skills:
            resume_skills = resume.skills
        else:
            resume_skills = extract_skills_from_resume(resume)
        
        # Calculate match score
        match_score = calculate_match_score(resume_skills, job_skills)

        # Add match score to resume metadata for reference
        setattr(resume, "match_score", match_score)
        scored_resumes.append((resume, match_score))

    # Sort resumes by match score in descending order
    sorted_resumes = [r[0] for r in sorted(scored_resumes, key=lambda x: x[1], reverse=True)]
    return sorted_resumes

def calculate_match_score(resume_skills: List[str], job_skills: List[str]) -> float:
    """Calculate a match score between resume skills and job skills."""
    if not job_skills or not resume_skills:
        return 0.0

    # Normalize skills to lowercase for comparison
    resume_skills_lower = [skill.lower() for skill in resume_skills if skill]
    job_skills_lower = [skill.lower() for skill in job_skills if skill]
    
    if not job_skills_lower:
        return 0.0

    # Count matching skills
    matching_skills = set(resume_skills_lower).intersection(set(job_skills_lower))

    # Calculate score as percentage of required skills matched
    match_percentage = len(matching_skills) / len(job_skills_lower) * 100
    return match_percentage

def rank_resumes_by_job_id(db: Session, job_id: int, user_id: int, folder_id: Optional[int] = None) -> List[Resume]:
    """
    Rank resumes based on the job ID by comparing resume metadata with job requirements.

    Args:
        db (Session): Database session.
        job_id (int): The ID of the job to rank resumes against.
        user_id (int): The ID of the user requesting the ranking.
        folder_id (Optional[int]): Filter resumes by folder ID if provided.

    Returns:
        List[Resume]: A list of resumes ranked by their match score.
    """
    # Fetch the job by ID
    job = db.query(JobModel).filter(JobModel.id == job_id, JobModel.user_id == user_id).first()
    if not job:
        logger.error(f"Job with ID {job_id} not found for user {user_id}.")
        return []

    # Extract skills from job metadata or parse job description
    job_skills = []
    if job.job_metadata and isinstance(job.job_metadata, dict) and "skills" in job.job_metadata:
        if isinstance(job.job_metadata["skills"], dict) and "required" in job.job_metadata["skills"]:
            job_skills = job.job_metadata["skills"]["required"]
        elif isinstance(job.job_metadata["skills"], list):
            job_skills = job.job_metadata["skills"]
            
    # If no skills found in metadata, parse job description
    if not job_skills:
        parser = TextParser()
        job_metadata = parser.parse_text(job.description, parse_type="job")
        if job_metadata and isinstance(job_metadata, dict) and "skills" in job_metadata:
            if isinstance(job_metadata["skills"], dict) and "required" in job_metadata["skills"]:
                job_skills = job_metadata["skills"]["required"]
            elif isinstance(job_metadata["skills"], list):
                job_skills = job_metadata["skills"]

    if not job_skills:
        logger.warning(f"No skills found for job ID {job_id}. Ranking will be inaccurate.")

    # Fetch resumes based on folder ID
    query = db.query(ResumeModel).filter(ResumeModel.user_id == user_id)
    if folder_id:
        query = query.filter(ResumeModel.folder_id == folder_id)
    resumes = query.all()

    if not resumes:
        logger.warning(f"No resumes found for user {user_id} in folder {folder_id if folder_id else 'any'}.")
        return []

    # Rank resumes based on match score
    scored_resumes = []
    for resume in resumes:
        # Get resume skills
        resume_skills = resume.skills or []
        if not resume_skills and resume.metadata:
            # Try to extract from metadata if skills field is empty
            metadata = resume.metadata
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
                    
            if isinstance(metadata, dict) and "skills" in metadata:
                if isinstance(metadata["skills"], list):
                    resume_skills = metadata["skills"]
        
        match_score = calculate_match_score(resume_skills, job_skills)

        # Add match score to resume metadata for reference
        setattr(resume, "match_score", match_score)
        scored_resumes.append((resume, match_score))

    # Sort resumes by match score in descending order
    sorted_resumes = [r[0] for r in sorted(scored_resumes, key=lambda x: x[1], reverse=True)]
    return sorted_resumes