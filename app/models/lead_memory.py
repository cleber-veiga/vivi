from sqlalchemy import Column, String, JSON, DateTime
from app.db.database import Base
from sqlalchemy.sql import func

class LeadMemory(Base):
    __tablename__ = 'lead_memory'

    phone = Column(String(20), primary_key=True, nullable=False)
    name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    cnpj = Column(String(100), nullable=True)
    corporate_reason = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    conversation_mem = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
