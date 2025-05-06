from typing import List, Dict, Any, Optional, Tuple
import logging
import json
import re
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
import numpy as np
from openai import AzureOpenAI
import os

from src.models.resume import Resume as ResumeModel
from src.schemas.resume import Resume
from src.models.job import Job as JobModel

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class HybridSearchService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HybridSearchService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            # Initialize OpenAI client for embeddings
            self.config = {
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "embedding_model": os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"),
                "max_token_length": 8191  # Max tokens for embedding model
            }

            self.client = AzureOpenAI(
                api_version=self.config["api_version"],
                azure_endpoint=self.config["azure_endpoint"],
                api_key=self.config["api_key"]
            )

            self.embedding_model = self.config["embedding_model"]
            self._initialized = True
            
            # Weights for hybrid search components
            self.weights = {
                "keyword": 0.7,  # weight for exact keyword matches
                "semantic": 0.3
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize HybridSearchService: {str(e)}")
            raise

    def _extract_resume_text(self, resume: ResumeModel) -> str:
        """Extract searchable text content from a resume."""
        text_parts = []
        
        # Add candidate name and email
        if resume.candidate_name:
            text_parts.append(f"Name: {resume.candidate_name}")
        if resume.candidate_email:
            text_parts.append(f"Email: {resume.candidate_email}")
            
        # Add skills
        if resume.skills and isinstance(resume.skills, list):
            skills_text = "Skills: " + ", ".join(resume.skills)
            text_parts.append(skills_text)
            
        # Add education
        if resume.education and isinstance(resume.education, list):
            for edu in resume.education:
                if isinstance(edu, dict):
                    degree = edu.get("degree", "")
                    institution = edu.get("institution", "")
                    if degree or institution:
                        text_parts.append(f"Education: {degree} at {institution}")
                        
        # Add experience
        if resume.experience and isinstance(resume.experience, list):
            for exp in resume.experience:
                if isinstance(exp, dict):
                    title = exp.get("title", "") or exp.get("job_title", "")
                    company = exp.get("company", "")
                    if title or company:
                        text_parts.append(f"Experience: {title} at {company}")
                        
        # Add parsed metadata if available
        if resume.parsed_metadata and isinstance(resume.parsed_metadata, dict):
            # Add additional sections that might be in parsed metadata
            for key, value in resume.parsed_metadata.items():
                if key not in ["skills", "education", "experience"] and value:
                    if isinstance(value, list):
                        text_parts.append(f"{key.capitalize()}: {', '.join(str(v) for v in value)}")
                    elif isinstance(value, dict):
                        text_parts.append(f"{key.capitalize()}: {json.dumps(value)}")
                    else:
                        text_parts.append(f"{key.capitalize()}: {value}")
        
        return "\n".join(text_parts)

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using OpenAI's embedding model."""
        try:
            # Truncate text if needed to fit model's context window
            truncated_text = text[:self.config["max_token_length"]]
            
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=truncated_text
            )
            
            # Extract the embedding from the response
            embedding = response.data[0].embedding
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return empty embedding in case of error
            return []

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
            
        try:
            a = np.array(vec1)
            b = np.array(vec2)
            
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0

    def _keyword_search(self, db: Session, query_terms: List[str], user_id: int, folder_id: Optional[int] = None) -> Dict[int, float]:
        """
        Perform improved keyword-based search on resumes.
        Returns a dictionary of resume_id -> normalized score
        """
        try:
            resume_scores = {}
            total_terms = len(query_terms)
            
            if total_terms == 0:
                return {}
                
            # Get all relevant resumes first
            base_query = db.query(ResumeModel).filter(ResumeModel.user_id == user_id)
            if folder_id:
                base_query = base_query.filter(ResumeModel.folder_id == folder_id)
                
            resumes = base_query.all()
            
            # Process each resume
            for resume in resumes:
                exact_matches = 0
                partial_matches = 0
                
                # Check for matches in skills
                if resume.skills and isinstance(resume.skills, list):
                    resume_skills = [skill.lower() for skill in resume.skills]
                    
                    for term in query_terms:
                        term_lower = term.lower()
                        
                        # Check for exact match
                        if term_lower in resume_skills:
                            exact_matches += 1
                        else:
                            # Check for partial match (term appears within skill)
                            for skill in resume_skills:
                                if term_lower in skill:
                                    partial_matches += 0.5
                                    break
                
                # Check for matches in education
                if resume.education and isinstance(resume.education, list):
                    for edu in resume.education:
                        if isinstance(edu, dict):
                            degree = edu.get("degree", "").lower()
                            institution = edu.get("institution", "").lower()
                            
                            for term in query_terms:
                                term_lower = term.lower()
                                if term_lower in degree or term_lower in institution:
                                    partial_matches += 0.3
                
                # Check for matches in experience
                if resume.experience and isinstance(resume.experience, list):
                    for exp in resume.experience:
                        if isinstance(exp, dict):
                            title = (exp.get("title", "") or exp.get("job_title", "")).lower()
                            company = exp.get("company", "").lower()
                            description = exp.get("description", "").lower()
                            
                            for term in query_terms:
                                term_lower = term.lower()
                                if term_lower in title:
                                    partial_matches += 0.4
                                elif term_lower in company:
                                    partial_matches += 0.3
                                elif term_lower in description:
                                    partial_matches += 0.2

                # Also check for matches in parsed_metadata if available
                if resume.parsed_metadata and isinstance(resume.parsed_metadata, dict):
                    # This is a simplified approach - you may want to expand this
                    metadata_str = json.dumps(resume.parsed_metadata).lower()
                    for term in query_terms:
                        term_lower = term.lower()
                        if term_lower in metadata_str:
                            partial_matches += 0.2
                
                # Calculate final score normalized to [0, 1]
                # Give higher weight to exact matches
                score = (exact_matches + (partial_matches * 0.5)) / total_terms
                
                # Bonus for exact matches to ensure they rank higher
                if exact_matches > 0:
                    score = min(1.0, score + 0.2)
                    
                resume_scores[resume.id] = score
                
            return resume_scores

        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            return {}

    def _semantic_search(self, db: Session, query_embedding: List[float], user_id: int, folder_id: Optional[int] = None) -> Dict[int, float]:
        """
        Perform semantic search based on embedding similarity.
        Returns a dictionary of resume_id -> similarity score
        """
        try:
            resume_scores = {}

            # Get all relevant resumes
            query = db.query(ResumeModel).filter(ResumeModel.user_id == user_id)
            if folder_id:
                query = query.filter(ResumeModel.folder_id == folder_id)

            resumes = query.all()

            # Calculate similarity for each resume
            for resume in resumes:
                # Use precomputed embedding if available
                resume_embedding = resume.embedding
                if not resume_embedding:
                    # Generate embedding if missing
                    resume_text = self._extract_resume_text(resume)
                    resume_embedding = self._get_embedding(resume_text)

                # Calculate similarity
                similarity = self._calculate_cosine_similarity(query_embedding, resume_embedding)
                resume_scores[resume.id] = similarity

            return resume_scores

        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return {}

    def _combine_scores(self, keyword_scores: Dict[int, float], semantic_scores: Dict[int, float], location_scores: Dict[int, float]) -> Dict[int, float]:
        """Combine keyword, semantic, and location scores using weighted average with priority for exact matches."""
        combined_scores = {}

        # Weights
        location_weight = 0.2
        keyword_weight = 0.6  # Slightly reduced from 0.7
        semantic_weight = 0.2  # Slightly reduced from 0.3

        # Get all unique resume IDs from all score sets
        all_resume_ids = set(keyword_scores.keys()) | set(semantic_scores.keys()) | set(location_scores.keys())

        for resume_id in all_resume_ids:
            keyword_score = keyword_scores.get(resume_id, 0.0)
            semantic_score = semantic_scores.get(resume_id, 0.0)
            location_score = location_scores.get(resume_id, 0.0)

            # Basic weighted average
            combined_score = (
                keyword_weight * keyword_score +
                semantic_weight * semantic_score +
                location_weight * location_score
            )

            # Boost score if there was a strong keyword match
            if keyword_score > 0.8:
                combined_score *= 1.2  # 20% boost for strong keyword matches
                combined_score = min(1.0, combined_score)  # Cap at 1.0

            combined_scores[resume_id] = combined_score

        return combined_scores

    def search_resumes(self, db: Session, query: str, user_id: int, folder_id: Optional[int] = None,
                   limit: int = 10, query_location: str = "") -> List[Tuple[ResumeModel, float]]:
        try:
            # Prepare query
            query = query.strip()
            if not query:
                return []

            # Extract query terms - improved tokenization
            query_terms = []
            # First try to extract quoted phrases
            quoted_phrases = re.findall(r'"([^"]*)"', query)
            for phrase in quoted_phrases:
                if phrase.strip():
                    query_terms.append(phrase.strip())
                    
            # Remove quoted phrases from the query string
            query = re.sub(r'"[^"]*"', '', query)
                    
            # Now extract remaining terms
            remaining_terms = [term.strip() for term in re.split(r'[,\s]+', query) if term.strip()]
            query_terms.extend(remaining_terms)

            # For semantic search, get embedding of full query
            query_embedding = self._get_embedding(query)

            # Perform keyword, semantic, and location searches
            keyword_scores = self._keyword_search(db, query_terms, user_id, folder_id)
            semantic_scores = self._semantic_search(db, query_embedding, user_id, folder_id)
            location_scores = self._location_match(db, query_location, user_id, folder_id)

            # Combine scores
            combined_scores = self._combine_scores(keyword_scores, semantic_scores, location_scores)

            # Sort by score
            sorted_resume_ids = sorted(combined_scores.keys(), key=lambda resume_id: combined_scores[resume_id], reverse=True)

            # Get debug information if needed
            debug_info = {}
            for resume_id in sorted_resume_ids[:limit]:
                debug_info[resume_id] = {
                    "keyword_score": keyword_scores.get(resume_id, 0),
                    "semantic_score": semantic_scores.get(resume_id, 0),
                    "location_score": location_scores.get(resume_id, 0),
                    "combined_score": combined_scores.get(resume_id, 0)
                }
            logger.debug(f"Search debug info: {json.dumps(debug_info)}")

            # Limit results
            top_resume_ids = sorted_resume_ids[:limit]

            # Fetch resume objects
            results = []
            for resume_id in top_resume_ids:
                resume = db.query(ResumeModel).filter(ResumeModel.id == resume_id).first()
                if resume:
                    score = combined_scores[resume_id]
                    # Add score as attribute
                    setattr(resume, "search_score", round(score * 100, 2))
                    results.append((resume, score))

            return results

        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return []
            
    # def search_by_job(self, db: Session, job_id: int, user_id: int, folder_id: Optional[int] = None,
    #                   limit: int = 10) -> List[Tuple[ResumeModel, float]]:
    #     """
    #     Search for resumes matching a specific job, including location-based matching.
    #     """
    #     try:
    #         # Fetch the job
    #         job = db.query(JobModel).filter(JobModel.id == job_id, JobModel.user_id == user_id).first()
    #         if not job:
    #             logger.error(f"Job with ID {job_id} not found for user {user_id}")
    #             return []

    #         # Extract search query from job
    #         job_title = job.title
    #         job_description = job.description
    #         job_role = job.role

    #         # Create search query from job details
    #         search_query = f"{job_title} {job_role}"

    #         # Extract skills from job metadata if available
    #         skills = []
    #         if job.job_metadata and isinstance(job.job_metadata, dict):
    #             # Get required skills
    #             if "skills" in job.job_metadata:
    #                 if isinstance(job.job_metadata["skills"], dict) and "required" in job.job_metadata["skills"]:
    #                     skills.extend(job.job_metadata["skills"]["required"])
    #                 elif isinstance(job.job_metadata["skills"], list):
    #                     skills.extend(job.job_metadata["skills"])

    #             if skills:
    #                 search_query += " " + " ".join(skills)

    #             # Extract location from job metadata
    #             job_location = job.job_metadata.get("location", "").lower()
    #         else:
    #             job_location = ""

    #         # Perform hybrid search with the job-based query
    #         return self.search_resumes(db, search_query, user_id, folder_id, limit, job_location)

    #     except Exception as e:
    #         logger.error(f"Error in job-based search: {str(e)}")
    #         return []

    def _location_match(self, db: Session, query_location: str, user_id: int, folder_id: Optional[int] = None) -> Dict[int, float]:
        """
        Perform location-based matching.
        Returns a dictionary of resume_id -> location match score.
        """
        try:
            resume_scores = {}

            # Normalize the query location
            query_location = query_location.lower()

            # Fetch resumes
            query = db.query(ResumeModel).filter(ResumeModel.user_id == user_id)
            if folder_id:
                query = query.filter(ResumeModel.folder_id == folder_id)

            resumes = query.all()

            for resume in resumes:
                # Extract resume location
                resume_location = (resume.parsed_metadata or {}).get("personal_info", {}).get("location", "").lower()

                # Check if the query location matches or is a parent region
                if query_location in resume_location or resume_location in query_location:
                    resume_scores[resume.id] = 1.0  # Full match
                elif query_location and resume_location:
                    # Partial match (e.g., Rajasthan and Jaipur)
                    resume_scores[resume.id] = 0.5  # Adjust score for partial match
                else:
                    resume_scores[resume.id] = 0.0  # No match

            return resume_scores

        except Exception as e:
            logger.error(f"Error in location matching: {str(e)}")
            return {}