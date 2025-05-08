import streamlit as st
from typing import Dict, Any, Optional, Tuple
import logging
import requests
from .api_service import APIService

logger = logging.getLogger(__name__)

class AuthService(APIService):
    """Service for authentication operations"""
    
    def login(self, username: str, password: str) -> bool:
        """Login user and store token"""
        try:
            response = requests.post(
                f"{self.base_url}/login",
                data={"username": username, "password": password}
            )
            
            # Handle response
            if response.status_code == 401:  # Unauthorized
                st.error("Incorrect username or password. Please try again.")
                return False
            elif response.status_code >= 400:  # Other client or server errors
                error_message = response.json().get("detail", "An error occurred.")
                st.error(f"Login failed: {error_message}")
                return False
            
            # Successful login
            data = self._handle_response(response)
            if "access_token" in data:
                st.session_state.access_token = data["access_token"]
                st.session_state.logged_in = True
                return True
            
            st.error("Unexpected response from the server.")
            return False
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            return False
    
    def signup(self, email: str, username: str, password: str, full_name: str) -> Tuple[bool, Optional[str]]:
        
        try:
            response = self.post(
                "signup",
                {
                    "email": email,
                    "username": username,
                    "password": password,
                    "full_name": full_name
                }
            )
            
            if "error" in response:
                return False, response["error"]
                
            return True, None
        except Exception as e:
            logger.exception(f"Signup failed: {str(e)}")
            return False, f"Signup failed: {str(e)}"
    
    def logout(self) -> None:
        """Clear user session"""
        if "access_token" in st.session_state:
            del st.session_state.access_token
        if "logged_in" in st.session_state:
            del st.session_state.logged_in
            
    def update_profile_image(self, user_id: int, image_url: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        
        try:
            response = self.put(
                f"users/{user_id}/profile-image",
                {"profile_image": image_url}
            )
            
            if "error" in response:
                return False, response["error"]
                
            return True, response
        except Exception as e:
            logger.exception(f"Profile image update failed: {str(e)}")
            return False, {"error": f"Update failed: {str(e)}"}
    
    def update_bio(self, user_id: int, bio: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Update user's bio
        
        Args:
            user_id: User ID
            bio: User's bio text
            
        Returns:
            (success, user_data or error_message)
        """
        try:
            response = self.put(
                f"users/{user_id}/bio",
                {"bio": bio}
            )
            
            if "error" in response:
                return False, response["error"]
                
            return True, response
        except Exception as e:
            logger.exception(f"Bio update failed: {str(e)}")
            return False, {"error": f"Update failed: {str(e)}"}