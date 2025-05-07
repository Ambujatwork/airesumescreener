from typing import Dict, List, Any, Optional, Tuple
import logging
from .api_service import APIService

logger = logging.getLogger(__name__)

class FolderService(APIService):
    """Service for folder operations"""
    
    def get_folders(self) -> List[Dict[str, Any]]:
        """
        Get all folders for current user
        
        Returns:
            List of folder objects
        """
        try:
            response = self.get("folders/")
            
            if isinstance(response, list):
                return response
            elif "error" in response:
                logger.error(f"Failed to get folders: {response['error']}")
                return []
            else:
                return []
        except Exception as e:
            logger.exception(f"Failed to get folders: {str(e)}")
            return []
    
    def create_folder(self, name: str, description: str = "") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Create a new folder
        
        Args:
            name: Folder name
            description: Folder description
            
        Returns:
            (success, folder_data or error_message)
        """
        try:
            response = self.post(
                "folders/",
                {"name": name, "description": description}
            )
            
            if "error" in response:
                return False, response["error"]
                
            return True, response
        except Exception as e:
            logger.exception(f"Failed to create folder: {str(e)}")
            return False, {"error": f"Failed to create folder: {str(e)}"}
    
    def delete_folder(self, folder_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a folder
        
        Args:
            folder_id: ID of the folder to delete
            
        Returns:
            (success, error_message)
        """
        try:
            response = self.delete(f"folders/{folder_id}")
            
            if "error" in response:
                return False, response["error"]
                
            return True, None
        except Exception as e:
            logger.exception(f"Failed to delete folder: {str(e)}")
            return False, f"Failed to delete folder: {str(e)}"
    
    def get_folder(self, folder_id: int) -> Optional[Dict[str, Any]]:
        """
        Get folder details
        
        Args:
            folder_id: ID of the folder to get
            
        Returns:
            Folder object or None if not found
        """
        try:
            response = self.get(f"folders/{folder_id}")
            
            if "error" in response:
                logger.error(f"Failed to get folder details: {response['error']}")
                return None
                
            return response
        except Exception as e:
            logger.exception(f"Failed to get folder details: {str(e)}")
            return None


class ResumeService(APIService):
    """Service for resume operations"""
    
    def upload_resumes(self, folder_id: int, files) -> List[Dict[str, Any]]:
        """
        Upload resumes to a folder
        
        Args:
            folder_id: ID of the folder to upload to
            files: List of file objects to upload
            
        Returns:
            List of uploaded resume objects
        """
        try:
            response = self.upload_files(
                f"folders/{folder_id}/upload_resumes",
                files
            )
            
            if isinstance(response, list):
                return response
            elif "error" in response:
                logger.error(f"Failed to upload resumes: {response['error']}")
                return []
            else:
                return []
        except Exception as e:
            logger.exception(f"Failed to upload resumes: {str(e)}")
            return []
    
    def get_resumes_by_folder(self, folder_id: int) -> List[Dict[str, Any]]:
        """
        Get all resumes in a folder
        
        Args:
            folder_id: ID of the folder to get resumes from
            
        Returns:
            List of resume objects
        """
        try:
            response = self.get(f"folders/{folder_id}/resumes")
            
            if isinstance(response, list):
                return response
            elif "error" in response:
                logger.error(f"Failed to get resumes: {response['error']}")
                return []
            else:
                return []
        except Exception as e:
            logger.exception(f"Failed to get resumes: {str(e)}")
            return []