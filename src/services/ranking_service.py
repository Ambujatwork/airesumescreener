from typing import List, Dict, Any, Optional
import json
import logging
from sqlalchemy.orm import Session
from src.schemas.resume import Resume
from src.models.resume import Resume as ResumeModel
from src.models.job import Job as JobModel
from src.services.text_parser import TextParser
from src.services.embedding_service import EmbeddingService
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def extract_skills_from_resume(resume: Resume) -> List[str]:
    skills = []
    
    try:
        if not resume.metadata:
            return []
            
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
    embedding_service = EmbeddingService()  

    job_metadata = parser.parse_text(job_description, parse_type="job")
    job_skills = []

    if job_metadata and isinstance(job_metadata, dict) and "skills" in job_metadata:
        if isinstance(job_metadata["skills"], dict) and "required" in job_metadata["skills"]:
            job_skills = job_metadata["skills"]["required"]
        elif isinstance(job_metadata["skills"], list):
            job_skills = job_metadata["skills"]

    if not job_skills:
        logger.warning("No job skills found in parsed metadata. Using keywords from description.")
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
        match_score = calculate_composite_match_score(resume, job_metadata, embedding_service)

        # Add match score to resume metadata for reference
        setattr(resume, "match_score", match_score)
        scored_resumes.append((resume, match_score))

    # Sort resumes by match score in descending order
    sorted_resumes = [r[0] for r in sorted(scored_resumes, key=lambda x: x[1], reverse=True)]
    return sorted_resumes

def calculate_composite_match_score(resume: Resume, job_metadata: dict, embedding_service: EmbeddingService) -> float:
    """
    Calculate a composite match score based on skills, experience, education, title, and location,
    including semantic similarity.
    """
    score = 0.0
    weights = {
        "skills": 0.3,
        "experience": 0.3,
        "education": 0.1,
        "title": 0.2,
        "location": 0.2
    }

    resume_metadata = resume.parsed_metadata or {}

    # Skills Match
    resume_skills = extract_skills_from_resume(resume)
    job_skills = extract_skills_from_job(job_metadata)
    skills_match = len(set(resume_skills).intersection(set(job_skills))) / max(len(job_skills), 1)

    # Experience Match (Semantic)
    resume_exp = resume.experience or resume_metadata.get("experience", [])
    job_exp = job_metadata.get("experience", [])
    experience_match = semantic_similarity_score(resume_exp, job_exp, embedding_service)

    # Education Match (Semantic)
    resume_edu = resume.education or resume_metadata.get("education", [])
    job_edu = job_metadata.get("education", [])
    education_match = semantic_similarity_score(resume_edu, job_edu, embedding_service)

    # Job Title Match
    resume_titles = [e.get("job_title", "").lower() for e in resume_exp if isinstance(e, dict)]
    job_title = (job_metadata.get("role") or "").lower()
    title_match = 1.0 if any(job_title in title for title in resume_titles) else 0.0

    # Location Match (Semantic)
    resume_location = resume_metadata.get("personal_info", {}).get("location", "").lower()
    job_location = job_metadata.get("location", "").lower()
    location_match = semantic_location_match(resume_location, job_location, embedding_service)

    # Weighted Score Calculation
    score += weights["skills"] * skills_match
    score += weights["experience"] * experience_match
    score += weights["education"] * education_match
    score += weights["title"] * title_match
    score += weights["location"] * location_match

    return round(score * 100, 2)

def rank_resumes_by_job_id(db: Session, job_id: int, user_id: int, folder_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Rank resumes based on the job ID by comparing resume metadata with job requirements.

    Returns:
        List[Dict[str, Any]]: A list of resumes with their match scores.
    """
    # Fetch the job by ID
    job = db.query(JobModel).filter(JobModel.id == job_id, JobModel.user_id == user_id).first()
    if not job:
        logger.error(f"Job with ID {job_id} not found for user {user_id}.")
        return []

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
        job_metadata = job.job_metadata or {}
        match_score = calculate_composite_match_score(resume, job_metadata, EmbeddingService())

        # Add match score to the response
        scored_resumes.append({
            "id": resume.id,
            "candidate_name": resume.candidate_name,
            "candidate_email": resume.candidate_email,
            "skills": resume.skills,
            "filename": resume.filename,
            "match_score": match_score
        })

    # Sort resumes by match score in descending order
    return sorted(scored_resumes, key=lambda x: x["match_score"], reverse=True)

def experience_overlap_score(resume_exp: List[dict], job_exp: List[dict]) -> float:
    """Check overlap in job titles and duration keywords."""
    if not resume_exp or not job_exp:
        return 0.0

    matched = 0
    job_titles = [j.get("job_title", "").lower() for j in job_exp if isinstance(j, dict)]

    for r in resume_exp:
        title = r.get("job_title", "").lower()
        if title and any(jt in title for jt in job_titles):
            matched += 1

    return matched / max(len(job_exp), 1)


def education_overlap_score(resume_edu: List[dict], job_edu: List[dict]) -> float:
    """Check overlap in degree or field of study."""
    if not resume_edu or not job_edu:
        return 0.0

    matched = 0
    job_degrees = [e.get("degree", "").lower() for e in job_edu if isinstance(e, dict)]
    job_fields = [e.get("field", "").lower() for e in job_edu if isinstance(e, dict)]

    for r in resume_edu:
        degree = r.get("degree", "").lower()
        field = r.get("field", "").lower()
        if degree in job_degrees or field in job_fields:
            matched += 1

    return matched / max(len(job_edu), 1)

def semantic_similarity_score(resume_field: List[str], job_field: List[str], embedding_service) -> float:
    """
    Calculate semantic similarity between resume and job fields using embeddings.

    Args:
        resume_field (List[str]): List of strings from the resume (e.g., education, experience).
        job_field (List[str]): List of strings from the job description.
        embedding_service (EmbeddingService): Service to generate embeddings.

    Returns:
        float: Semantic similarity score between 0 and 1.
    """
    if not resume_field or not job_field:
        return 0.0

    try:
        # Combine all text in the field into a single string
        resume_text = " ".join(resume_field)
        job_text = " ".join(job_field)

        # Generate embeddings
        resume_embedding = embedding_service.generate_embedding(resume_text)
        job_embedding = embedding_service.generate_embedding(job_text)

        # Check if embeddings are valid
        if not resume_embedding or not job_embedding:
            return 0.0

        # Calculate cosine similarity
        similarity = cosine_similarity(
            [resume_embedding], [job_embedding]
        )[0][0]

        # Normalize similarity to [0, 1]
        return max(0.0, min(1.0, similarity))

    except Exception as e:
        logger.error(f"Error calculating semantic similarity: {str(e)}")
        return 0.0

def semantic_location_match(resume_location: str, job_location: str, embedding_service: EmbeddingService) -> float:
    """
    Calculate semantic similarity between resume and job locations using embeddings.
    """
    if not resume_location or not job_location:
        return 0.0

    try:
        # Generate embeddings for locations
        resume_embedding = embedding_service.generate_embedding(resume_location)
        job_embedding = embedding_service.generate_embedding(job_location)

        # Check if embeddings are valid
        if not resume_embedding or not job_embedding:
            return 0.0

        # Calculate cosine similarity
        similarity = cosine_similarity([resume_embedding], [job_embedding])[0][0]

        # Log the similarity score
        logger.info(f"Resume Location: {resume_location}, Job Location: {job_location}, Similarity: {similarity}")

        # Normalize similarity to [0, 1]
        return max(0.0, min(1.0, similarity))

    except Exception as e:
        logger.error(f"Error calculating semantic similarity for locations: {str(e)}")
        return 0.0
