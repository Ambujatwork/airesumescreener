from typing import Dict, List, Any, Optional, Tuple
import logging
from .api_service import APIService

logger = logging.getLogger(__name__)

class JobService(APIService):
    """Service for job operations"""
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all jobs for current user
        
        Returns:
            List of job objects
        """
        try:
            response = self.get("jobs/")
            
            if isinstance(response, list):
                return response
            elif "error" in response:
                logger.error(f"Failed to get jobs: {response['error']}")
                return []
            else:
                return []
        except Exception as e:
            logger.exception(f"Failed to get jobs: {str(e)}")
            return []
    
    def create_job(self, title: str, description: str, required_skills: List[str], role: str = "") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Create a new job
        
        Args:
            title: Job title
            description: Job description
            required_skills: List of required skills
            role: Job role (defaults to empty string to satisfy NOT NULL constraint)
            
        Returns:
            (success, job_data or error_message)
        """
        try:
            response = self.post(
                "jobs/",
                {
                    "title": title, 
                    "description": description,
                    "required_skills": required_skills,
                    "role": role  # Always provide a value for role
                }
            )
            
            if "error" in response:
                return False, response["error"]
                
            return True, response
        except Exception as e:
            logger.exception(f"Failed to create job: {str(e)}")
            return False, {"error": f"Failed to create job: {str(e)}"}
    
    def delete_job(self, job_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a job
        
        Args:
            job_id: ID of the job to delete
            
        Returns:
            (success, error_message)
        """
        try:
            response = self.delete(f"jobs/{job_id}")
            
            if "error" in response:
                return False, response["error"]
                
            return True, None
        except Exception as e:
            logger.exception(f"Failed to delete job: {str(e)}")
            return False, f"Failed to delete job: {str(e)}"
    
    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get job details
        
        Args:
            job_id: ID of the job to get
            
        Returns:
            Job object or None if not found
        """
        try:
            response = self.get(f"jobs/{job_id}")
            
            if "error" in response:
                logger.error(f"Failed to get job details: {response['error']}")
                return None
                
            return response
        except Exception as e:
            logger.exception(f"Failed to get job details: {str(e)}")
            return None
    
    def rank_candidates(self, job_id: int, folder_id: Optional[int] = None, top_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Rank candidates for a job
        
        Args:
            job_id: ID of the job to rank candidates against
            folder_id: Optional ID of the folder to filter candidates from
            top_n: Optional number of top candidates to return
            
        Returns:
            List of ranked resume objects
        """
        try:
            params = {"job_id": job_id}
            if folder_id:
                params["folder_id"] = folder_id
            if top_n:
                params["top_n"] = top_n
                
            response = self.get("jobs/candidates/rank", params)
            
            if isinstance(response, list):
                return response
            elif "error" in response:
                logger.error(f"Failed to rank candidates: {response['error']}")
                return []
            else:
                return []
        except Exception as e:
            logger.exception(f"Failed to rank candidates: {str(e)}")
            return []


class SearchService(APIService):
    """Service for search operations"""
    
    def search_resumes(self, query: str, folder_id: Optional[int] = None, limit: int = 10) -> Dict[str, Any]:
        
        try:
            params = {"query": query, "limit": limit}
            if folder_id:
                params["folder_id"] = folder_id
            
            response = self.get("search/resumes", params)
            
            if "error" in response:
                logger.error(f"Failed to search resumes: {response['error']}")
                return {"results": [], "total": 0}
            
            return response
        except Exception as e:
            logger.exception(f"Failed to search resumes: {str(e)}")
            return {"results": [], "total": 0}