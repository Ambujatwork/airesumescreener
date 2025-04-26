import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DIAL_CONFIG = {
        "api_key": os.getenv("AZURE_API_KEY"),
        "azure_endpoint": os.getenv("AZURE_ENDPOINT"),
        "api_version": os.getenv("AZURE_API_VERSION"),
        "model": os.getenv("AZURE_MODEL"),
        "max_workers": int(os.getenv("AZURE_MAX_WORKERS", 5))
        
    }