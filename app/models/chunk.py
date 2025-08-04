from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from pgvector.sqlalchemy import Vector
from app.db.database import Base
from sqlalchemy.sql import func

class Chunk(Base):
    __tablename__ = "chunk"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("document.id"))
    page = Column(Integer)
    content = Column(Text)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
