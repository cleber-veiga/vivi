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
        name: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        cnpj: Optional[str] = None,
        corporate_reason: Optional[str] = None,
        metadata_json: Optional[Dict] = None,
    ) -> LeadMemory:
        
        stmt = select(LeadMemory).where(LeadMemory.phone == phone).limit(1)
        result = await session.execute(stmt)
        lead = result.scalar_one_or_none()

        if lead:
            lead.conversation_mem = memory
            flag_modified(lead, "conversation_mem")

            if name: lead.name = name
            if email: lead.email = email
            if address: lead.address = address
            if cnpj: lead.cnpj = cnpj
            if corporate_reason: lead.corporate_reason = corporate_reason
            if metadata_json: lead.metadata_json = metadata_json
        else:
            lead = LeadMemory(
                phone=phone,
                name=name,
                email=email,
                address=address,
                cnpj=cnpj,
                corporate_reason=corporate_reason,
                metadata_json=metadata_json,
                conversation_mem=memory,
            )
            session.add(lead)

        await session.commit()
        await session.refresh(lead)
        return lead
