import streamlit as st
from typing import Dict, Any, Optional, Tuple
import logging
from .api_service import APIService

logger = logging.getLogger(__name__)

class AuthService(APIService):
    """Service for authentication operations"""
    
    def login(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Login user and store token
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            (success, error_message)
        """
        try:
            # Auth requires form data, not JSON
            response = self.post(
                "login",
                {"username": username, "password": password},
                as_json=False
            )
            
            if "error" in response:
                return False, response["error"]
                
            if "access_token" in response:
                st.session_state.access_token = response["access_token"]
                st.session_state.logged_in = True
                return True, None
                
            return False, "Invalid response from server"
        except Exception as e:
            logger.exception(f"Login failed: {str(e)}")
            return False, f"Login failed: {str(e)}"
    
    def signup(self, email: str, username: str, password: str, full_name: str) -> Tuple[bool, Optional[str]]:
        """
        Register a new user
        
        Args:
            email: User's email
            username: User's username
            password: User's password
            full_name: User's full name
            
        Returns:
            (success, error_message)
        """
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
        """
        Update user's profile image
        
        Args:
            user_id: User ID
            image_url: URL of the profile image
            
        Returns:
            (success, user_data or error_message)
        """
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