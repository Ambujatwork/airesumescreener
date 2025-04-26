from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True, index = True)
    title = Column(String, nullable = False )
    description = Column(Text, nullable = False)
    role = Column(String, nullable = False)
    job_metadata = Column(Text, nullable = False)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default = datetime.utcnow)


    user = relationship("User", back_populates = "jobs")