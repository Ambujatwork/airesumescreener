from fastapi import FastAPI, Depends, HTTPException, Request, Header
from .routers import auth, folders, jobs
from .database import engine, Base
from dotenv import load_dotenv
import os
from src.models.user import User
from src.dependencies.security import get_current_user

load_dotenv()

print(f"AZURE_OPENAI_API_KEY: {os.getenv('AZURE_OPENAI_API_KEY')}")
print(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
print(f"AZURE_OPENAI_API_VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
# Print environment variables for debugging (remove in production)
print(f"DATABASE_URL set: {'Yes' if os.getenv('DATABASE_URL') else 'No'}")
print(f"SECRET_KEY set: {'Yes' if os.getenv('SECRET_KEY') else 'No'}")
print(f"MONGO_URL set: {'Yes' if os.getenv('MONGO_URL') else 'No'}")

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(jobs.router)

@app.get("/")
def read_root():
    return {"message": "Resume Screener API"}

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": "This is a protected route", "user": current_user.email}

@app.get("/check-token")
async def check_token(authorization: str = Header(None)):
    """Debug endpoint to check token format"""
    if not authorization:
        return {"error": "No authorization header provided"}
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return {"error": "Invalid authorization format. Must be 'Bearer <token>'"}
    
    token = parts[1]
    return {
        "token_provided": True,
        "token_format_valid": True,
        "token_preview": token[:10] + "..." + token[-10:] if len(token) > 20 else token
    }

