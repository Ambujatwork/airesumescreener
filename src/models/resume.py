from sqlalchemy import Column, Integer, String, ARRAY, ForeignKey, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base
from src.models import User

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    mongo_id = Column(String, index=True)  # Reference to MongoDB document
    folder_id = Column(Integer, ForeignKey("folders.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Extracted metadata
    candidate_name = Column(String, nullable=True)
    candidate_email = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    experience = Column(JSON, nullable=True)
    parsed_metadata = Column(JSON, nullable=True)  

    embedding = Column(ARRAY(Float), nullable=True)
    embedding_updated_at = Column(DateTime, nullable=True)
    content_hash = Column(String, nullable=False, index=True)
    # Relationships
    folder = relationship("Folder", back_populates="resumes")  # Use string reference
    user = relationship("User")  # Use string reference
