from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class Agent(Base):
    __tablename__ = "agent"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    oauth_token_id = Column(Integer, ForeignKey("oauth_token.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    oauth_token = relationship("OAuthToken", backref="agents", lazy="joined")