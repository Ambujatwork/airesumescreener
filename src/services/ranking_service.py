from typing import List, Dict, Any
import json
import logging
from src.schemas.resume import Resume

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
        
        # Extract technical skills
        if isinstance(metadata, dict) and "skills" in metadata:
            if isinstance(metadata["skills"], dict):
                # Extract from structured skills object
                if "technical" in metadata["skills"] and isinstance(metadata["skills"]["technical"], list):
                    skills.extend([s.lower() for s in metadata["skills"]["technical"] if isinstance(s, str)])
                
                if "soft" in metadata["skills"] and isinstance(metadata["skills"]["soft"], list):
                    skills.extend([s.lower() for s in metadata["skills"]["soft"] if isinstance(s, str)])
            elif isinstance(metadata["skills"], list):
                # Extract from flat skills list
                skills.extend([s.lower() for s in metadata["skills"] if isinstance(s, str)])
                
        # Extract additional skills from experience
        if isinstance(metadata, dict) and "experience" in metadata and isinstance(metadata["experience"], list):
            for exp in metadata["experience"]:
                if isinstance(exp, dict) and "responsibilities" in exp and isinstance(exp["responsibilities"], list):
                    # Extract skill keywords from responsibilities
                    for resp in exp["responsibilities"]:
                        if isinstance(resp, str):
                            # Split on commas and common separators
                            parts = resp.replace(",", " ").replace(";", " ").split()
                            skills.extend([p.lower() for p in parts if len(p) > 3])  # Filter out short words
    
    except Exception as e:
        logger.error(f"Error extracting skills from resume: {str(e)}")
    
    # Remove duplicates and return
    return list(set(skills))

def extract_skills_from_job(job_metadata: str) -> List[str]:
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
                # If not valid JSON, use basic text splitting
                return [s.lower() for s in job_metadata.split() if len(s) > 3]
        
        # Extract required skills
        if isinstance(metadata, dict) and "skills" in metadata:
            if isinstance(metadata["skills"], dict):
                # Extract from structured skills object
                if "required" in metadata["skills"] and isinstance(metadata["skills"]["required"], list):
                    required_skills.extend([s.lower() for s in metadata["skills"]["required"] if isinstance(s, str)])
            elif isinstance(metadata["skills"], list):
                # Extract from flat skills list
                required_skills.extend([s.lower() for s in metadata["skills"] if isinstance(s, str)])
                
        # Extract from qualifications
        if isinstance(metadata, dict) and "qualifications" in metadata and isinstance(metadata["qualifications"], list):
            for qual in metadata["qualifications"]:
                if isinstance(qual, str):
                    # Split on commas and common separators
                    parts = qual.replace(",", " ").replace(";", " ").split()
                    required_skills.extend([p.lower() for p in parts if len(p) > 3])
    
    except Exception as e:
        logger.error(f"Error extracting skills from job: {str(e)}")
    
    # Remove duplicates and return
    return list(set(required_skills))

def calculate_match_score(resume_skills: List[str], job_skills: List[str]) -> float:
    """Calculate a match score between resume skills and job skills."""
    if not job_skills:
        return 0.0
        
    # Count matching skills
    matching_skills = set(resume_skills).intersection(set(job_skills))
    
    # Calculate score as percentage of required skills matched
    match_percentage = len(matching_skills) / len(job_skills) * 100 if job_skills else 0
    
    return match_percentage

def rank_resumes_by_job_metadata(resumes: List[Resume], job_metadata: str) -> List[Resume]:
    """Rank resumes based on matching with job metadata."""
    try:
        # Extract skills from job
        job_skills = extract_skills_from_job(job_metadata)
        
        # Score each resume
        scored_resumes = []
        for resume in resumes:
            resume_skills = extract_skills_from_resume(resume)
            match_score = calculate_match_score(resume_skills, job_skills)
            
            # Add match score to resume metadata for reference
            if not hasattr(resume, "match_score"):
                setattr(resume, "match_score", match_score)
            
            scored_resumes.append((resume, match_score))
        
        # Sort by match score (descending)
        sorted_resumes = [r[0] for r in sorted(scored_resumes, key=lambda x: x[1], reverse=True)]
        
        return sorted_resumes
        
    except Exception as e:
        logger.error(f"Error ranking resumes: {str(e)}")
        # Return unsorted resumes as fallback
        return resumes