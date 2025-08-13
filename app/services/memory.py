import json
from sqlalchemy.orm import Session
from app.models.lead_memory import LeadMemory
from sqlalchemy.exc import NoResultFound
from typing import Any, Optional, Dict
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.chunk import Chunk
from app.models.document import Document
from sqlalchemy import select, delete
from app.src.embedding import EmbeddingProcessor
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timezone

def _parse_desafios(texto: Optional[str]) -> list[str]:
    if not texto:
        return []
    try:
        data = json.loads(texto)
        # garante lista de strings
        return [str(x) for x in data] if isinstance(data, list) else []
    except Exception:
        # se não for JSON válido, trata como "um único valor" antigo
        return [texto.strip()] if texto.strip() else []

def _dump_desafios(lista: list[str]) -> str:
    return json.dumps(lista, ensure_ascii=False)

def _parse_videos(texto: Optional[str]) -> list[str]:
    if not texto:
        return []
    try:
        data = json.loads(texto)
        return [str(x) for x in data] if isinstance(data, list) else []
    except Exception:
        return [texto.strip()] if texto.strip() else []

def _dump_videos(lista: list[str]) -> str:
    return json.dumps(lista, ensure_ascii=False)

class MemoryService:

    @staticmethod
    async def get_memory_by_phone(session: AsyncSession, phone: str) -> Optional[LeadMemory]:
        stmt = select(LeadMemory).where(LeadMemory.phone == phone).limit(1)
        result = await session.execute(stmt)
        lead = result.scalar_one_or_none()
        return lead
    
    @staticmethod
    async def delete_memory_by_phone(session: AsyncSession, phone: str) -> bool:
        try:
            stmt = delete(LeadMemory).where(LeadMemory.phone == phone)
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            return False

    @staticmethod
    async def upsert_memory(
        session: AsyncSession,
        phone: str,
        memory: Optional[Dict] = None,
        metadata_json: Optional[Dict] = None,
        **kwargs
    ) -> LeadMemory:
        # Hard filter: nunca processar 'desafios'
        if "desafios" in kwargs:
            kwargs.pop("desafios", None)

        stmt = select(LeadMemory).where(LeadMemory.phone == phone).limit(1)
        result = await session.execute(stmt)
        lead = result.scalar_one_or_none()

        if lead:
            # Atualiza a memória só se foi informada
            if memory is not None:
                lead.conversation_mem = memory
                flag_modified(lead, "conversation_mem")

            # Atualiza apenas campos válidos, não nulos e != 'desafios'
            for key, value in kwargs.items():
                if key != "desafios" and hasattr(lead, key) and value is not None:
                    setattr(lead, key, value)
                    # Caso algum desses campos seja JSON, marque como modificado
                    if key in ("metadata_json", "conversation_mem", "videos_enviados"):
                        flag_modified(lead, key)

            if metadata_json is not None:
                lead.metadata_json = metadata_json
                flag_modified(lead, "metadata_json")

        else:
            lead_data = {"phone": phone}
            if memory is not None:
                lead_data["conversation_mem"] = memory
            if metadata_json is not None:
                lead_data["metadata_json"] = metadata_json

            model_fields = {c.name for c in LeadMemory.__table__.columns}
            for key, value in kwargs.items():
                if key != "desafios" and key in model_fields and value is not None:
                    lead_data[key] = value

            lead = LeadMemory(**lead_data)
            session.add(lead)

        await session.commit()
        await session.refresh(lead)
        return lead

    @staticmethod
    async def add_video_enviado(
        session: AsyncSession,
        phone: str,
        video: str
    ) -> "LeadMemory":
        stmt = (
            select(LeadMemory)
            .where(LeadMemory.phone == phone)
            .with_for_update()
            .limit(1)
        )
        result = await session.execute(stmt)
        lead: Optional[LeadMemory] = result.scalar_one_or_none()

        novo = (video or "").strip()
        if not novo:
            raise ValueError("Vídeo vazio não é permitido.")

        if not lead:
            videos_list = [novo]
            lead = LeadMemory(phone=phone, videos_enviados=_dump_videos(videos_list))
            session.add(lead)
        else:
            atuais = _parse_videos(lead.videos_enviados)
            if novo not in atuais:
                atuais.append(novo)
                lead.videos_enviados = _dump_videos(atuais)

        await session.commit()
        await session.refresh(lead)
        return lead
    
    @staticmethod
    async def add_desafio_cliente(
        session: AsyncSession,
        phone: str,
        desafio: str,   # <- sempre string
    ) -> "LeadMemory":
        # normaliza input
        novo = (desafio or "").strip()
        if not novo:
            raise ValueError("Desafio vazio não é permitido.")

        stmt = (
            select(LeadMemory)
            .where(LeadMemory.phone == phone)
            .with_for_update()
            .limit(1)
        )
        result = await session.execute(stmt)
        lead: Optional[LeadMemory] = result.scalar_one_or_none()

        if not lead:
            desafios_list = [novo]
            lead = LeadMemory(phone=phone, desafios=_dump_desafios(desafios_list))
            session.add(lead)
        else:
            atuais = _parse_desafios(lead.desafios)
            if novo not in atuais:
                atuais.append(novo)
                lead.desafios = _dump_desafios(atuais)

        await session.commit()
        await session.refresh(lead)
        return lead

def _coerce_to_messages_container(mem: Optional[Any]) -> tuple[Any, List[Dict[str, str]], str]:
    """
    Retorna (container, messages_ref, container_type)

    - Se a memória for uma LISTA de mensagens, mantém como lista.
    - Se for um DICT com 'messages', usa essa lista.
    - Se houver 'history' (legado), migra para 'messages' com o shape {role, content}.
    - Se não existir nada, cria uma lista vazia.
    """
    # Caso 1: já é lista de mensagens [{"role","content"}, ...]
    if isinstance(mem, list):
        return mem, mem, "list"

    # Caso 2: é dict
    if isinstance(mem, dict):
        # Migra history -> messages, se existir e não houver messages
        if "messages" not in mem:
            if isinstance(mem.get("history"), list):
                msgs = []
                for h in mem["history"]:
                    if isinstance(h, dict):
                        role = h.get("role")
                        text = h.get("text")
                        if role in ("user", "assistant") and isinstance(text, str):
                            msgs.append({"role": role, "content": text})
                mem["messages"] = msgs
                mem.pop("history", None)

        # Garante 'messages'
        if not isinstance(mem.get("messages"), list):
            mem["messages"] = []

        return mem, mem["messages"], "dict"

    # Caso 3: vazio / outro tipo -> lista nova
    mem_list: List[Dict[str, str]] = []
    return mem_list, mem_list, "list"


async def record_llm_followup_like_previous(
    session,
    phone: str,
    text: str,
    *,
    max_items: int = 200
) -> None:
    """
    Anexa a mensagem do LLM no mesmo formato das interações anteriores:
    {"role": "assistant", "content": "<texto>"}

    - Preserva o container original (lista ou dict com 'messages').
    - Opcionalmente migra 'history' legado para 'messages'.
    - Limita o tamanho do histórico.
    """
    try:
        lead = await MemoryService.get_memory_by_phone(session, phone)
        base_mem = None
        if lead and getattr(lead, "conversation_mem", None) is not None:
            base_mem = lead.conversation_mem  # pode ser list ou dict(JSON)

        container, messages_ref, container_type = _coerce_to_messages_container(base_mem)

        # Anexa no formato correto
        entry = {"role": "assistant", "content": (text or "").strip()}
        messages_ref.append(entry)

        # Enxuga histórico, se necessário
        if len(messages_ref) > max_items:
            del messages_ref[: len(messages_ref) - max_items]

        # Persiste sem alterar outros campos
        await MemoryService.upsert_memory(
            session=session,
            phone=phone,
            memory=container
        )
    except Exception as e:
        print(f"[followup] erro ao registrar memória (formato anterior) para {phone}: {e}")