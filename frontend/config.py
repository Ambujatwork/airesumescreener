import os
from typing import Dict, Any, Optional
import streamlit as st

class AppConfig:
    """Configuration manager for the application"""

    # Default configuration
    _DEFAULTS = {
        "api_url": "http://localhost:8000",
        "app_name": "ResumeMatch Pro",
        "app_icon": "📄",
        "theme_primary_color": "#1E88E5",
        "theme_secondary_color": "#FFC107",
        "max_upload_size_mb": 10,
        "allowed_extensions": ["pdf", "docx", "doc"],
        "default_results_limit": 10
    }

    @classmethod
    def get(cls, key: str) -> Any:
        """Get configuration value with fallbacks:
        1. Environment variable
        2. Streamlit secrets
        3. Default value
        """
        env_key = f"RESUMEMATCH_{key.upper()}"
        
        # Check environment variables
        if env_key in os.environ:
            return os.environ[env_key]
        
        # Check Streamlit secrets
        try:
            return st.secrets[key]
        except (KeyError, FileNotFoundError):
            pass
        
        # Return default or None
        return cls._DEFAULTS.get(key)

    @classmethod
    def load_theme(cls) -> None:
        """Apply theme configuration to Streamlit"""
        st.set_page_config(
            page_title=cls.get("app_name"),
            page_icon=cls.get("app_icon"),
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Apply custom CSS
        primary_color = cls.get("theme_primary_color")
        secondary_color = cls.get("theme_secondary_color")
        
        st.markdown(f"""
        <style>
        .stApp {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .stButton>button {{
            background-color: {primary_color};
            color: white;
        }}
        .stProgress > div > div > div > div {{
            background-color: {primary_color};
        }}
        h1, h2, h3 {{
            color: {primary_color};
        }}
        </style>
        """, unsafe_allow_html=True)

    @classmethod
    def get_api_url(cls) -> str:
        """Convenience method to get API URL"""
        return cls.get("api_url")

    @classmethod
    def get_allowed_extensions(cls) -> list:
        """Get list of allowed file extensions"""
        return cls.get("allowed_extensions")

    @classmethod
    def get_max_upload_size(cls) -> int:
        """Get maximum upload size in MB"""
        return int(cls.get("max_upload_size_mb"))