from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

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
    
    folder = relationship("Folder", back_populates="resumes")
    user = relationship("User")