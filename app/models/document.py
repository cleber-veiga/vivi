from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class Document(Base):
    __tablename__ = "document"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    agent_id = Column(Integer, ForeignKey("agent.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
