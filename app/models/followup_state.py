from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from app.db.database import Base

class FollowUpState(Base):
    __tablename__ = "followup_state"

    phone = Column(String, primary_key=True)  # E.164 sem 'whatsapp:+'
    last_actor = Column(String)  # 'user' | 'ai'
    last_ai_at = Column(DateTime(timezone=True), nullable=True)
    schedule_confirmed = Column(Boolean, default=False)
    followup_count = Column(Integer, server_default="0", nullable=False)
    last_followup_at = Column(DateTime(timezone=True), nullable=True)
    followup_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
