from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from src.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    username = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    profile_image = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    


    folders = relationship("Folder", back_populates="user")
    jobs = relationship("Job", back_populates = 'user')