from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import socket

load_dotenv()

# Get the original DATABASE_URL from environment variables
original_db_url = os.getenv("DATABASE_URL")

# Function to check if a host is available
def is_host_available(host, port=5432, timeout=1):
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except (socket.timeout, socket.error):
        return False

# Parse the DATABASE_URL to get components
if original_db_url and "db" in original_db_url:
    # If "db" is in the URL but not available, replace with localhost
    if not is_host_available("db"):
        DATABASE_URL = original_db_url.replace("@db:", "@localhost:")
    else:
        DATABASE_URL = original_db_url
else:
    # Fallback if DATABASE_URL is not set
    db_user = os.getenv("POSTGRES_USER", "admin")
    db_password = os.getenv("POSTGRES_PASSWORD", "secret")
    db_name = os.getenv("POSTGRES_DB", "resume_screener")
    
    # Try db first, fallback to localhost if not available
    if is_host_available("db"):
        db_host = "db"
    else:
        db_host = "localhost"
    
    DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"

print(f"Using DATABASE_URL: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()