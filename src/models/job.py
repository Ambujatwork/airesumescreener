from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, ARRAY, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base
from sqlalchemy.dialects.postgresql import JSONB
from src.models import User

class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True, index = True)
    title = Column(String, nullable = False )
    description = Column(Text, nullable = False)
    role = Column(String, nullable = False)
    job_metadata = Column(JSONB, nullable = False)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default = datetime.utcnow)

    embedding = Column(ARRAY(Float), nullable=True)
    embedding_updated_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates = "jobs")