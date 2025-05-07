from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import asyncio
import json

from .embedding_service import EmbeddingService
from src.models.resume import Resume
from src.models.job import Job
from src.database_mongo import resumes_collection

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Manager for handling embedding generation and updates for resumes and jobs"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    async def update_resume_embeddings(
        self, 
        db: Session,
        resume_ids: Optional[List[int]] = None,
        force_update: bool = False
    ) -> Dict[int, bool]:
        """Update embeddings using Postgres Resume data"""
        results = {}
        
        # Query resumes needing updates
        query = db.query(Resume)
        if resume_ids:
            query = query.filter(Resume.id.in_(resume_ids))
        if not force_update:
            query = query.filter((Resume.embedding.is_(None)) | (Resume.embedding_updated_at.is_(None)))
            
        resumes = query.all()
        logger.info(f"Found {len(resumes)} resumes needing embedding updates")
        
        for resume in resumes:
            try:
                # Generate embedding from Postgres fields
                text_for_embedding = self._prepare_resume_text_for_embedding(resume)
                embedding = await self.embedding_service.generate_embedding(text_for_embedding)
                
                # Update resume
                resume.embedding = embedding
                resume.embedding_updated_at = datetime.utcnow()
                db.commit()
                
                results[resume.id] = True
                logger.info(f"Updated embedding for resume {resume.id}")
                
            except Exception as e:
                logger.error(f"Error updating resume {resume.id}: {str(e)}")
                db.rollback()
                results[resume.id] = False
                
        return results
        
    async def update_job_embeddings(self, db: Session, job_ids: Optional[List[int]] = None) -> Dict[int, bool]:
        
        results = {}
        
        # Query for jobs
        query = db.query(Job)
        if job_ids:
            query = query.filter(Job.id.in_(job_ids))
            
        jobs = query.all()
        logger.info(f"Generating embeddings for {len(jobs)} jobs")
        
        job_embeddings = {}
        
        for job in jobs:
            try:
                # Generate embedding from job description
                text_for_embedding = self._prepare_job_text_for_embedding(job)
                embedding = await self.embedding_service.generate_embedding(text_for_embedding)
                
                job.embedding = embedding
                job.embedding_updated_at = datetime.utcnow()

                db.commit()
                results[job.id] = True
                logger.info(f"Successfully generated embedding for job {job.id}")
                
            except Exception as e:
                logger.error(f"Error generating embedding for job {job.id}: {str(e)}")
                db.rollback()
                results[job.id] = False
                
        return results
        
    def _prepare_resume_text_for_embedding(self, resume: Resume) -> str:
        """Construct embedding text from Postgres Resume fields"""
        text_parts = []
        
        # Candidate info
        if resume.candidate_name:
            text_parts.append(f"Name: {resume.candidate_name}")
        if resume.candidate_email:
            text_parts.append(f"Email: {resume.candidate_email}")
        
        # Skills
        if resume.skills:
            skills_text = ", ".join(resume.skills) if isinstance(resume.skills, list) else str(resume.skills)
            text_parts.append(f"Skills: {skills_text}")
        
        # Education
        if resume.education:
            education_text = self._format_education(resume.education)
            text_parts.append(f"Education: {education_text}")
        
        # Experience
        if resume.experience:
            experience_text = self._format_experience(resume.experience)
            text_parts.append(f"Experience: {experience_text}")
        
        # Additional metadata
        if resume.parsed_metadata:
            metadata = resume.parsed_metadata
            # Add other metadata fields if needed
            # Example: certifications, projects, etc.
        
        return "\n\n".join(text_parts)
    
    def _prepare_job_text_for_embedding(self, job: Job) -> str:
        """
        Prepare job description text for embedding by combining structured and unstructured data.
        
        Args:
            job: Job model object
            
        Returns:
            Formatted text for embedding
        """
        text_parts = []
        
        # Add job title and role
        text_parts.append(f"Title: {job.title}")
        text_parts.append(f"Role: {job.role}")
        
        # Add structured metadata if available
        if job.job_metadata:
            metadata = job.job_metadata
            
            # Add required skills
            if "required_skills" in metadata and metadata["required_skills"]:
                if isinstance(metadata["required_skills"], list):
                    skills_text = ", ".join(metadata["required_skills"])
                    text_parts.append(f"Required Skills: {skills_text}")
            
            # Add preferred skills
            if "preferred_skills" in metadata and metadata["preferred_skills"]:
                if isinstance(metadata["preferred_skills"], list):
                    skills_text = ", ".join(metadata["preferred_skills"])
                    text_parts.append(f"Preferred Skills: {skills_text}")
            
            # Add required experience
            if "required_experience" in metadata and metadata["required_experience"]:
                text_parts.append(f"Required Experience: {metadata['required_experience']}")
                
            # Add education requirements
            if "education_requirements" in metadata and metadata["education_requirements"]:
                text_parts.append(f"Education Requirements: {metadata['education_requirements']}")
        
        # Add full description at the end
        if job.description:
            text_parts.append(job.description)
            
        return "\n\n".join(text_parts)
    
    def _format_education(self, education_data) -> str:
        """Format education data into a string"""
        if isinstance(education_data, list):
            education_items = []
            for edu in education_data:
                if isinstance(edu, dict):
                    institution = edu.get("institution", "")
                    degree = edu.get("degree", "")
                    field = edu.get("field", "")
                    year = edu.get("year", "")
                    
                    parts = []
                    if institution:
                        parts.append(institution)
                    if degree:
                        parts.append(degree)
                    if field:
                        parts.append(field)
                    if year:
                        parts.append(str(year))
                        
                    education_items.append(" - ".join(parts))
                elif isinstance(edu, str):
                    education_items.append(edu)
                    
            return "; ".join(education_items)
        return str(education_data)
    
    def _format_experience(self, experience_data) -> str:
        """Format experience data into a string"""
        if isinstance(experience_data, list):
            experience_items = []
            for exp in experience_data:
                if isinstance(exp, dict):
                    company = exp.get("company", "")
                    title = exp.get("title", "")
                    description = exp.get("description", "")
                    
                    parts = []
                    if company:
                        parts.append(company)
                    if title:
                        parts.append(title)
                    if description and isinstance(description, str):
                        # Truncate long descriptions
                        parts.append(description[:200] + ("..." if len(description) > 200 else ""))
                        
                    experience_items.append(" - ".join(parts))
                elif isinstance(exp, str):
                    experience_items.append(exp)
                    
            return "; ".join(experience_items)
        return str(experience_data)