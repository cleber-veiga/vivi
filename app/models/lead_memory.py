from sqlalchemy import Column, String, JSON, DateTime, Integer
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
    uf = Column(String(10), nullable=True)
    cidade  = Column(String(255), nullable=True)
    quantidade_usuarios = Column(Integer, nullable=True)
    sistema_atual  = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    conversation_mem = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
