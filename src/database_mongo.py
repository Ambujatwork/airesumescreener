from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "resume_screener")

mongo_client = AsyncIOMotorClient(MONGO_URL)
mongo_db = mongo_client[MONGO_DB]

# Collections
resumes_collection = mongo_db["resumes"]