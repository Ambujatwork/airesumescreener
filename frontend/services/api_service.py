import requests
import json
import streamlit as st
from typing import Dict, List, Any, Optional, Union
from config import AppConfig
import logging

logger = logging.getLogger(__name__)

class APIService:
    """Base class for API services"""
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize API service with base URL"""
        self.base_url = base_url or AppConfig.get_api_url()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        token = st.session_state.get("access_token", "")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
    
    def _handle_response(self, response: requests.Response, 
                        expected_status_code: int = 200,
                        error_message: str = "API request failed") -> Any:
        """Handle API response and errors"""
        if response.status_code != expected_status_code:
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", f"Error {response.status_code}")
                logger.error(f"API error: {error_detail}")
                
                # Return a user-friendly error
                return {"error": error_detail}
            except Exception as e:
                logger.exception(f"Failed to parse error response: {str(e)}")
                return {"error": f"{error_message} ({response.status_code})"}
        
        try:
            return response.json()
        except Exception as e:
            logger.exception(f"Failed to parse JSON response: {str(e)}")
            return {"error": "Failed to parse response"}
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make GET request to API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()
            
            logger.debug(f"GET {url} with params {params}")
            response = requests.get(url, headers=headers, params=params)
            
            return self._handle_response(response)
        except Exception as e:
            logger.exception(f"GET request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
    
    def post(self, endpoint: str, data: Any, as_json: bool = True) -> Any:
        """Make POST request to API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()
            
            logger.debug(f"POST {url}")
            
            if as_json:
                headers["Content-Type"] = "application/json"
                response = requests.post(url, headers=headers, json=data)
            else:
                response = requests.post(url, headers=headers, data=data)
            
            return self._handle_response(response, expected_status_code=201)
        except Exception as e:
            logger.exception(f"POST request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
    
    def put(self, endpoint: str, data: Any) -> Any:
        """Make PUT request to API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()
            headers["Content-Type"] = "application/json"
            
            logger.debug(f"PUT {url}")
            response = requests.put(url, headers=headers, json=data)
            
            return self._handle_response(response)
        except Exception as e:
            logger.exception(f"PUT request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
    
    def delete(self, endpoint: str) -> Any:
        """Make DELETE request to API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()
            
            logger.debug(f"DELETE {url}")
            response = requests.delete(url, headers=headers)
            
            return self._handle_response(response, expected_status_code=204)
        except Exception as e:
            logger.exception(f"DELETE request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}
    
    def upload_files(self, endpoint: str, files: List[Any], 
                    data: Optional[Dict[str, Any]] = None) -> Any:
        """Upload files to API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()
            # Don't set Content-Type for multipart/form-data
            
            files_data = []
            for i, file in enumerate(files):
                if hasattr(file, 'name') and hasattr(file, 'getvalue'):
                    # Handle Streamlit uploaded files
                    files_data.append(
                        ('files', (file.name, file.getvalue(), f"application/{file.type}"))
                    )
            
            logger.debug(f"POST (files) {url}")
            response = requests.post(url, headers=headers, files=files_data, data=data)
            
            return self._handle_response(response, expected_status_code=201)
        except Exception as e:
            logger.exception(f"File upload failed: {str(e)}")
            return {"error": f"Upload failed: {str(e)}"}