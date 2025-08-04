from sqlalchemy import Column, Integer, String, DateTime
from app.db.database import Base
from sqlalchemy.sql import func

class Agent(Base):
    __tablename__ = "agent"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)