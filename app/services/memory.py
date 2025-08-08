from sqlalchemy.orm import Session
from app.models.lead_memory import LeadMemory
from sqlalchemy.exc import NoResultFound
from typing import Optional, Dict
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.chunk import Chunk
from app.models.document import Document
from sqlalchemy import select
from app.src.embedding import EmbeddingProcessor
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified


class MemoryService:

    @staticmethod
    async def get_memory_by_phone(session: AsyncSession, phone: str) -> Optional[LeadMemory]:
        stmt = select(LeadMemory).where(LeadMemory.phone == phone).limit(1)
        result = await session.execute(stmt)
        lead = result.scalar_one_or_none()
        return lead

    @staticmethod
    async def upsert_memory(
        session: AsyncSession,
        phone: str,
        memory: Dict,
        metadata_json: Optional[Dict] = None,
        **kwargs  # campos dinâmicos: name, email, address, etc.
    ) -> LeadMemory:
        """
        Atualiza ou insere dados do lead no banco, incluindo memória e campos dinâmicos.
        """

        stmt = select(LeadMemory).where(LeadMemory.phone == phone).limit(1)
        result = await session.execute(stmt)
        lead = result.scalar_one_or_none()

        if lead:
            lead.conversation_mem = memory
            flag_modified(lead, "conversation_mem")

            # Atualiza somente os campos válidos da tabela LeadMemory
            for key, value in kwargs.items():
                if hasattr(lead, key) and value is not None:
                    setattr(lead, key, value)

            if metadata_json:
                lead.metadata_json = metadata_json
        else:
            lead_data = {
                "phone": phone,
                "conversation_mem": memory,
                "metadata_json": metadata_json,
            }

            # Filtra somente os campos válidos da model
            model_fields = {c.name for c in LeadMemory.__table__.columns}
            for key, value in kwargs.items():
                if key in model_fields and value is not None:
                    lead_data[key] = value

            lead = LeadMemory(**lead_data)
            session.add(lead)

        await session.commit()
        await session.refresh(lead)
        return lead

