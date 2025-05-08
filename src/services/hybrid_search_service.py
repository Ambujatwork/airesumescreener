from typing import List, Dict, Any, Optional, Tuple
import logging
import json
import re
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
import numpy as np
from openai import AzureOpenAI
import os
from datetime import datetime, timedelta

from src.models.resume import Resume as ResumeModel
from src.schemas.resume import Resume
from src.models.job import Job as JobModel
from .embedding_service import EmbeddingService  # Import the existing service

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
            # Initialize embedding service for reuse
            self.embedding_service = EmbeddingService()
            
            # Configuration for embedding updates
            self.embedding_freshness_days = 30  # Consider embeddings older than this to be stale
            
            # Configure weights for hybrid search components
            self.weights = {
                "keyword": 0.5,    # Weight for exact and partial keyword matches
                "semantic": 0.4,    # Weight for semantic similarity
                "location": 0.1     # Weight for location matching
            }
            
            # Domain-specific terms dictionary to improve tokenization
            self.domain_terms = {
                "programming": ["python", "java", "javascript", "js", "typescript", "ts", "c++", "c#", "ruby", "php"],
                "frameworks": ["react", "angular", "vue", "django", "flask", "spring", "asp.net"],
                "database": ["sql", "nosql", "postgresql", "mysql", "mongodb", "oracle", "dynamodb"],
                "cloud": ["aws", "azure", "gcp", "google cloud", "cloud computing"],
                "roles": ["frontend", "front-end", "backend", "back-end", "fullstack", "full-stack", "devops", "sre"]
            }
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize ImprovedHybridSearchService: {str(e)}")
            raise

    def _extract_resume_text(self, resume: ResumeModel) -> str:
        """Extract searchable text content from a resume with improved structure."""
        text_parts = []
        
        # Add candidate information with more weight
        if resume.candidate_name:
            text_parts.append(f"Candidate Name: {resume.candidate_name}")
        if resume.candidate_email:
            text_parts.append(f"Email: {resume.candidate_email}")
            
        # Add skills with emphasis
        if resume.skills and isinstance(resume.skills, list):
            text_parts.append(f"Skills: {', '.join(resume.skills)}")
            # Add skills again to give them more weight in the embedding
            for skill in resume.skills:
                text_parts.append(f"Has skill: {skill}")
            
        # Add education with better structure
        if resume.education and isinstance(resume.education, list):
            education_parts = []
            for edu in resume.education:
                if isinstance(edu, dict):
                    degree = edu.get("degree", "")
                    institution = edu.get("institution", "")
                    field = edu.get("field", "")
                    year = edu.get("year", "")
                    
                    edu_str = []
                    if degree:
                        edu_str.append(degree)
                    if field:
                        edu_str.append(f"in {field}")
                    if institution:
                        edu_str.append(f"from {institution}")
                    if year:
                        edu_str.append(f"({year})")
                        
                    education_parts.append(" ".join(edu_str))
            
            if education_parts:
                text_parts.append(f"Education: {'; '.join(education_parts)}")
                        
        # Add experience with better structure
        if resume.experience and isinstance(resume.experience, list):
            for idx, exp in enumerate(resume.experience):
                if isinstance(exp, dict):
                    title = exp.get("title", "") or exp.get("job_title", "")
                    company = exp.get("company", "")
                    description = exp.get("description", "")
                    
                    exp_parts = []
                    if title:
                        exp_parts.append(f"Position: {title}")
                    if company:
                        exp_parts.append(f"Company: {company}")
                    if description:
                        # Add a shortened version of the description
                        exp_parts.append(f"Description: {description[:200]}")
                        
                    if exp_parts:
                        text_parts.append(f"Experience {idx+1}: {' | '.join(exp_parts)}")
                        
        # Add location information if available
        if resume.parsed_metadata and isinstance(resume.parsed_metadata, dict):
            location = resume.parsed_metadata.get("personal_info", {}).get("location", "")
            if location:
                text_parts.append(f"Location: {location}")
            
            # Add other relevant metadata
            for key, value in resume.parsed_metadata.items():
                if key not in ["personal_info", "skills", "education", "experience"] and value:
                    if isinstance(value, list):
                        text_parts.append(f"{key.capitalize()}: {', '.join(str(v) for v in value)}")
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            if v and k != "location":  # Location already added above
                                text_parts.append(f"{key.capitalize()} - {k}: {v}")
        
        return "\n".join(text_parts)

    def _ensure_embedding(self, db: Session, resume: ResumeModel) -> List[float]:
        """Ensure resume has an up-to-date embedding."""
        needs_update = False
        
        # Check if embedding exists
        if not resume.embedding:
            needs_update = True
        # Check if embedding is stale
        elif resume.embedding_updated_at:
            cutoff_date = datetime.utcnow() - timedelta(days=self.embedding_freshness_days)
            if resume.embedding_updated_at < cutoff_date:
                needs_update = True
        else:
            needs_update = True
            
        if needs_update:
            try:
                # Extract text for embedding
                resume_text = self._extract_resume_text(resume)
                
                # Generate embedding
                embedding = self.embedding_service.generate_embedding(resume_text)
                
                # Update resume object
                resume.embedding = embedding
                resume.embedding_updated_at = datetime.utcnow()
                db.commit()
                
                return embedding
            except Exception as e:
                logger.error(f"Error updating embedding for resume {resume.id}: {str(e)}")
                db.rollback()
                return resume.embedding or []
        else:
            return resume.embedding

    def _parse_search_query(self, query: str) -> Dict[str, Any]:
        """
        Parse search query into structured components for more effective searching.
        Returns dictionary with extracted terms, skills, roles, etc.
        """
        parsed_query = {
            "original_query": query,
            "quoted_phrases": [],
            "skills": [],
            "roles": [],
            "general_terms": [],
            "domain_terms": {}
        }
        
        # Extract quoted phrases
        quoted_phrases = re.findall(r'"([^"]*)"', query)
        parsed_query["quoted_phrases"] = [phrase.strip() for phrase in quoted_phrases if phrase.strip()]
        
        # Remove quoted phrases from query
        clean_query = re.sub(r'"[^"]*"', '', query)
        
        # Extract remaining terms
        terms = [term.strip().lower() for term in re.split(r'[,\s]+', clean_query) if term.strip()]
        
        # Categorize terms
        for term in terms:
            # Check for domain-specific terms
            domain_matched = False
            for domain, domain_terms in self.domain_terms.items():
                if term in domain_terms:
                    if domain not in parsed_query["domain_terms"]:
                        parsed_query["domain_terms"][domain] = []
                    parsed_query["domain_terms"][domain].append(term)
                    domain_matched = True
                    break
            
            # Check if it's a role
            if term in self.domain_terms["roles"]:
                parsed_query["roles"].append(term)
            # Assume it might be a skill
            elif len(term) > 2 and not term.isdigit():  # Basic filtering
                parsed_query["skills"].append(term)
            
            # Add to general terms if not matched to a specific category
            if not domain_matched and term not in parsed_query["roles"]:
                parsed_query["general_terms"].append(term)
        
        return parsed_query

    def _keyword_search(self, db: Session, parsed_query: Dict[str, Any], user_id: int, folder_id: Optional[int] = None) -> Dict[int, float]:
        """
        Improved keyword-based search using parsed query components.
        Returns a dictionary of resume_id -> normalized score
        """
        try:
            resume_scores = {}
            
            # Prepare query terms for matching
            all_terms = parsed_query["general_terms"] + parsed_query["skills"] + parsed_query["roles"]
            # Add domain terms
            for domain_terms in parsed_query["domain_terms"].values():
                all_terms.extend(domain_terms)
            # Add quoted phrases
            all_terms.extend(parsed_query["quoted_phrases"])
            
            # Deduplicate
            all_terms = list(set(all_terms))
            
            if not all_terms:
                return {}
                
            # Weight multipliers for different term types
            weights = {
                "exact_skill": 1.0,
                "partial_skill": 0.5,
                "exact_title": 0.9,
                "partial_title": 0.4,
                "exact_company": 0.7,
                "partial_company": 0.3,
                "description": 0.2,
                "education": 0.6,
                "quoted_phrase": 1.2,  # Higher weight for exact phrases
            }
                
            # Get all relevant resumes
            base_query = db.query(ResumeModel).filter(ResumeModel.user_id == user_id)
            if folder_id:
                base_query = base_query.filter(ResumeModel.folder_id == folder_id)
                
            resumes = base_query.all()
            total_terms = len(all_terms)
            
            # Process each resume
            for resume in resumes:
                score = 0.0
                matches = {}
                
                # Check for matches in skills
                if resume.skills and isinstance(resume.skills, list):
                    resume_skills = [skill.lower() for skill in resume.skills]
                    
                    for term in all_terms:
                        term_lower = term.lower()
                        
                        # Check for exact skill match
                        if term_lower in resume_skills:
                            matches[f"skill_{term}"] = weights["exact_skill"]
                        else:
                            # Check for partial skill match
                            for skill in resume_skills:
                                if term_lower in skill:
                                    matches[f"skill_partial_{term}"] = weights["partial_skill"]
                                    break
                
                # Check for matches in experience
                if resume.experience and isinstance(resume.experience, list):
                    for exp in resume.experience:
                        if isinstance(exp, dict):
                            title = (exp.get("title", "") or exp.get("job_title", "")).lower()
                            company = exp.get("company", "").lower()
                            description = exp.get("description", "").lower()
                            
                            for term in all_terms:
                                term_lower = term.lower()
                                
                                # Title matches
                                if term_lower == title:
                                    matches[f"title_exact_{term}"] = weights["exact_title"]
                                elif term_lower in title:
                                    matches[f"title_partial_{term}"] = weights["partial_title"]
                                    
                                # Company matches
                                if term_lower == company:
                                    matches[f"company_exact_{term}"] = weights["exact_company"]
                                elif term_lower in company:
                                    matches[f"company_partial_{term}"] = weights["partial_company"]
                                    
                                # Description matches
                                if term_lower in description:
                                    matches[f"description_{term}"] = weights["description"]
                
                # Check for matches in education
                if resume.education and isinstance(resume.education, list):
                    for edu in resume.education:
                        if isinstance(edu, dict):
                            degree = edu.get("degree", "").lower()
                            institution = edu.get("institution", "").lower()
                            field = edu.get("field", "").lower()
                            
                            for term in all_terms:
                                term_lower = term.lower()
                                if term_lower in degree or term_lower in field or term_lower in institution:
                                    matches[f"education_{term}"] = weights["education"]
                
                # Special handling for quoted phrases
                for phrase in parsed_query["quoted_phrases"]:
                    phrase_lower = phrase.lower()
                    
                    # Check in skills
                    if resume.skills and isinstance(resume.skills, list):
                        skills_text = " ".join(resume.skills).lower()
                        if phrase_lower in skills_text:
                            matches[f"quoted_skills_{phrase}"] = weights["quoted_phrase"]
                    
                    # Check in experience
                    if resume.experience and isinstance(resume.experience, list):
                        for exp in resume.experience:
                            if isinstance(exp, dict):
                                title = (exp.get("title", "") or exp.get("job_title", "")).lower()
                                company = exp.get("company", "").lower()
                                description = exp.get("description", "").lower()
                                
                                if phrase_lower in title or phrase_lower in company or phrase_lower in description:
                                    matches[f"quoted_exp_{phrase}"] = weights["quoted_phrase"]
                
                # Calculate final score
                if matches:
                    # Sum of weights, normalized by total possible score
                    max_possible_score = total_terms * max(weights.values())
                    score = min(1.0, sum(matches.values()) / max_possible_score)
                    
                    # Add a multiplier based on the number of unique terms matched
                    unique_terms_matched = len(set([key.split('_')[-1] for key in matches.keys()]))
                    coverage_ratio = unique_terms_matched / total_terms
                    score = score * (0.7 + 0.3 * coverage_ratio)  # Adjust balance between match quality and coverage
                    
                resume_scores[resume.id] = score
                
            return resume_scores

        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            return {}

    def _semantic_search(self, db: Session, query: str, user_id: int, parsed_query: Dict[str, Any], folder_id: Optional[int] = None) -> Dict[int, float]:
        """
        Perform improved semantic search with query enhancement.
        """
        try:
            resume_scores = {}
            
            # Enhanced query for semantic search
            enhanced_query = query
            
            # Add domain-specific context if available
            domain_contexts = []
            for domain, terms in parsed_query["domain_terms"].items():
                if terms:
                    domain_contexts.append(f"{domain.capitalize()}: {', '.join(terms)}")
            
            if domain_contexts:
                enhanced_query += "\n\nContext: " + "; ".join(domain_contexts)
                
            # Add role context if available
            if parsed_query["roles"]:
                enhanced_query += f"\n\nRoles: {', '.join(parsed_query['roles'])}"
                
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(enhanced_query)

            # Get all relevant resumes
            query = db.query(ResumeModel).filter(ResumeModel.user_id == user_id)
            if folder_id:
                query = query.filter(ResumeModel.folder_id == folder_id)

            resumes = query.all()

            # Calculate similarity for each resume with embedding update
            for resume in resumes:
                # Ensure up-to-date embedding
                resume_embedding = self._ensure_embedding(db, resume)
                if not resume_embedding:
                    continue

                # Calculate similarity
                similarity = self.embedding_service.compute_similarity(query_embedding, resume_embedding)
                resume_scores[resume.id] = similarity

            return resume_scores

        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return {}

    def _location_match(self, db: Session, query_location: str, user_id: int, folder_id: Optional[int] = None) -> Dict[int, float]:
        """
        Improved location-based matching with region hierarchies.
        """
        try:
            resume_scores = {}
            
            if not query_location.strip():
                # Return empty scores if no location query
                return resume_scores

            # Normalize the query location
            query_location = query_location.lower().strip()
            
            # Define region hierarchies (simplified example)
            # In production, this could be expanded or loaded from a database
            region_hierarchies = {
                "usa": ["california", "new york", "texas", "washington"],
                "california": ["san francisco", "los angeles", "san diego"],
                "new york": ["new york city", "buffalo", "albany"],
                "india": ["delhi", "maharashtra", "karnataka", "tamil nadu", "Rajasthan"],
                "delhi": ["new delhi", "gurgaon", "noida"],
                "Rajasthan" : ["jaipur", "udaipur", "jodhpur"],
                "karnataka": ["bangalore", "mysore", "mangalore"],
                "maharashtra": ["mumbai", "pune", "nagpur"],
                "uk": ["london", "manchester", "birmingham"]
            }

            # Fetch resumes
            query = db.query(ResumeModel).filter(ResumeModel.user_id == user_id)
            if folder_id:
                query = query.filter(ResumeModel.folder_id == folder_id)

            resumes = query.all()

            for resume in resumes:
                # Extract resume location
                resume_location = ""
                if resume.parsed_metadata and isinstance(resume.parsed_metadata, dict):
                    resume_location = resume.parsed_metadata.get("personal_info", {}).get("location", "").lower()
                
                if not resume_location:
                    continue
                    
                # Check for different match types
                if query_location == resume_location:
                    # Exact match
                    resume_scores[resume.id] = 1.0
                elif query_location in resume_location:
                    # Query location is part of resume location (e.g. "York" in "New York")
                    resume_scores[resume.id] = 0.9
                elif resume_location in query_location:
                    # Resume location is part of query location (e.g. "New York" in "New York City")
                    resume_scores[resume.id] = 0.8
                else:
                    # Check hierarchical relationships
                    
                    # Is query location a parent region of resume location?
                    if query_location in region_hierarchies and resume_location in region_hierarchies[query_location]:
                        resume_scores[resume.id] = 0.85
                        
                    # Is resume location a parent region of query location?
                    elif resume_location in region_hierarchies and query_location in region_hierarchies[resume_location]:
                        resume_scores[resume.id] = 0.75
                        
                    # Are they siblings in the same region?
                    else:
                        for parent, children in region_hierarchies.items():
                            if query_location in children and resume_location in children:
                                resume_scores[resume.id] = 0.7
                                break
                        else:
                            # No direct relationship found
                            # Do a fuzzy token-based comparison for partial matches
                            query_tokens = set(query_location.split())
                            resume_tokens = set(resume_location.split())
                            common_tokens = query_tokens.intersection(resume_tokens)
                            
                            if common_tokens:
                                # Some common location terms
                                similarity = len(common_tokens) / max(len(query_tokens), len(resume_tokens))
                                resume_scores[resume.id] = 0.5 * similarity
                            else:
                                resume_scores[resume.id] = 0.0

            return resume_scores

        except Exception as e:
            logger.error(f"Error in location matching: {str(e)}")
            return {}

    def _combine_scores(self, keyword_scores: Dict[int, float], semantic_scores: Dict[int, float], 
                       location_scores: Dict[int, float]) -> Dict[int, float]:
        """Combine scores with dynamic weighting based on query characteristics."""
        combined_scores = {}

        # Get all unique resume IDs from all score sets
        all_resume_ids = set(keyword_scores.keys()) | set(semantic_scores.keys()) | set(location_scores.keys())

        for resume_id in all_resume_ids:
            keyword_score = keyword_scores.get(resume_id, 0.0)
            semantic_score = semantic_scores.get(resume_id, 0.0)
            location_score = location_scores.get(resume_id, 0.0)

            # Calculate the weighted score
            weighted_score = (
                self.weights["keyword"] * keyword_score +
                self.weights["semantic"] * semantic_score +
                self.weights["location"] * location_score
            )
            
            # Additional boosting logic
            
            # Boost if both keyword and semantic scores are high (indicates strong relevance)
            if keyword_score > 0.7 and semantic_score > 0.7:
                weighted_score *= 1.15  # 15% boost
                
            # Boost if exact keyword match and good semantic score (relevant context)
            if keyword_score > 0.9 and semantic_score > 0.5:
                weighted_score *= 1.1  # 10% boost
                
            # Location bonus for relevant matches
            if location_score > 0.8 and (keyword_score > 0.5 or semantic_score > 0.5):
                weighted_score *= 1.05  # 5% boost
                
            # Cap at 1.0
            weighted_score = min(1.0, weighted_score)
            
            combined_scores[resume_id] = weighted_score

        return combined_scores

    def search_resumes(self, db: Session, query: str, user_id: int, folder_id: Optional[int] = None,
                   limit: int = 10, query_location: str = "") -> List[Tuple[ResumeModel, float]]:
        """
        Main search method that combines keyword, semantic, and location-based searches.
        """
        try:
            # Prepare query
            query = query.strip()
            if not query:
                return []

            # Parse the query into structured components
            parsed_query = self._parse_search_query(query)
            logger.debug(f"Parsed query: {parsed_query}")

            # Perform the three types of searches
            keyword_scores = self._keyword_search(db, parsed_query, user_id, folder_id)
            semantic_scores = self._semantic_search(db, query, user_id, parsed_query, folder_id)
            location_scores = self._location_match(db, query_location, user_id, folder_id)

            # Combine scores using weighted approach
            combined_scores = self._combine_scores(keyword_scores, semantic_scores, location_scores)

            # Sort by score
            sorted_resume_ids = sorted(combined_scores.keys(), key=lambda resume_id: combined_scores[resume_id], reverse=True)

            # Generate debug info
            debug_info = {}
            for resume_id in sorted_resume_ids[:limit]:
                debug_info[resume_id] = {
                    "keyword_score": round(keyword_scores.get(resume_id, 0), 3),
                    "semantic_score": round(semantic_scores.get(resume_id, 0), 3),
                    "location_score": round(location_scores.get(resume_id, 0), 3),
                    "combined_score": round(combined_scores.get(resume_id, 0), 3)
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
                    # Add score as attribute for display
                    setattr(resume, "search_score", round(score * 100, 2))
                    # Add component scores for debugging
                    setattr(resume, "keyword_score", round(keyword_scores.get(resume_id, 0) * 100, 2))
                    setattr(resume, "semantic_score", round(semantic_scores.get(resume_id, 0) * 100, 2))
                    setattr(resume, "location_score", round(location_scores.get(resume_id, 0) * 100, 2))
                    results.append((resume, score))

            return results

        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return []
            
    def search_by_job(self, db: Session, job_id: int, user_id: int, folder_id: Optional[int] = None,
                      limit: int = 10) -> List[Tuple[ResumeModel, float]]:
        """
        Search for resumes matching a specific job using semantic job matching.
        """
        try:
            # Fetch the job
            job = db.query(JobModel).filter(JobModel.id == job_id, JobModel.user_id == user_id).first()
            if not job:
                logger.error(f"Job with ID {job_id} not found for user {user_id}")
                return []

            # Extract search components from job
            job_title = job.title or ""
            job_description = job.description or ""
            job_role = job.role or ""

            # Extract skills and location from job metadata
            skills = []
            job_location = ""
            
            if job.job_metadata and isinstance(job.job_metadata, dict):
                # Extract required skills
                if "skills" in job.job_metadata:
                    if isinstance(job.job_metadata["skills"], dict):
                        if "required" in job.job_metadata["skills"]:
                            skills.extend(job.job_metadata["skills"]["required"])
                        if "preferred" in job.job_metadata["skills"]:
                            skills.extend(job.job_metadata["skills"]["preferred"])
                    elif isinstance(job.job_metadata["skills"], list):
                        skills.extend(job.job_metadata["skills"])
                
                # Direct skills list
                if "required_skills" in job.job_metadata and isinstance(job.job_metadata["required_skills"], list):
                    skills.extend(job.job_metadata["required_skills"])
                if "preferred_skills" in job.job_metadata and isinstance(job.job_metadata["preferred_skills"], list):
                    skills.extend(job.job_metadata["preferred_skills"])
                    
                # Extract location
                job_location = job.job_metadata.get("location", "")
            
            # Generate a comprehensive search query
            search_query = f"{job_title} {job_role}"
            if skills:
                unique_skills = list(set(skills))  # Remove duplicates
                search_query += f" {' '.join(unique_skills)}"
            
            # Add key requirements from description (simplified)
            if job_description:
                # Extract first paragraph or up to 200 chars as summary
                summary = job_description.split('\n\n')[0][:200]
                search_query += f" {summary}"
                
            logger.info(f"Generated job search query: {search_query[:100]}...")
            
            # Use the standard search method with the job-based query
            return self.search_resumes(db, search_query, user_id, folder_id, limit, job_location)

        except Exception as e:
            logger.error(f"Error in job-based search: {str(e)}")
            return []
            
    def adjust_weights(self, keyword_weight: float = None, semantic_weight: float = None, location_weight: float = None):
        """
        Adjust the weights used in hybrid search.
        This allows tuning the search algorithm based on feedback.
        """
        weights_sum = 0
        
        if keyword_weight is not None:
            self.weights["keyword"] = max(0.0, min(1.0, keyword_weight))
            weights_sum += self.weights["keyword"]
            
        if semantic_weight is not None:
            self.weights["semantic"] = max(0.0, min(1.0, semantic_weight))
            weights_sum += self.weights["semantic"]
            
        if location_weight is not None:
            self.weights["location"] = max(0.0, min(1.0, location_weight))
            weights_sum += self.weights["location"]
            
        # Normalize weights if they sum to more than 1
        if weights_sum > 1.0:
            factor = 1.0 / weights_sum
            for key in self.weights:
                self.weights[key] *= factor
                
        logger.info(f"Search weights adjusted to: {self.weights}")
        
        return self.weights