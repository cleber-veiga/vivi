from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.chunk import Chunk
from app.models.document import Document
from sqlalchemy import select
from app.src.embedding import EmbeddingProcessor
from sqlalchemy.ext.asyncio import AsyncSession

class ChunkProcessor:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def split_text(self, text: str) -> List[str]:
        return self.splitter.split_text(text)
    
    def generate_chunks(self, document_id: int, content: str) -> List[Chunk]:
        raw_chunks = self.split_text(content)

        # Gera embeddings para os textos
        embedding_processor = EmbeddingProcessor()
        vectors = embedding_processor.embed_openai(raw_chunks)

        # Cria os objetos Chunk com texto + embedding
        return [
            Chunk(
                document_id=document_id,
                page=i + 1,
                content=chunk_text,
                embedding=vector
            )
            for i, (chunk_text, vector) in enumerate(zip(raw_chunks, vectors))
        ]

class ChunkRetrive:
    def __init__(self, session: AsyncSession):
        self.embedding = EmbeddingProcessor()
        self.session = session

    async def retrieve(self, query: str, document_name: str):
        # Log 1: Verifica a query recebida
        print(f"[🔍 DEBUG] Consulta recebida: {query}")
        print(f"[🔍 DEBUG] Documento alvo: {document_name}")

        # Gera o vetor da consulta
        query_vector = self.embedding.embed_openai([query])[0]
        print(f"[🧠 DEBUG] Vetor da pergunta (dim={len(query_vector)}): {query_vector[:5]}...")

        # Monta a query
        stmt = (
            select(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.name == document_name)
            .order_by(Chunk.embedding.l2_distance(query_vector))
            .limit(3)
            .select_from(Chunk)
        )

        print(f"[🧾 DEBUG] Query SQL montada:\n{stmt}")

        # Executa
        results = await self.session.execute(stmt)
        chunks = results.scalars().all()

        print(f"[📦 DEBUG] Total de chunks retornados: {len(chunks)}")

        if not chunks:
            print("[⚠️ AVISO] Nenhum chunk foi encontrado para o documento informado. Verifique se o nome está correto e se os embeddings existem.")

        return "\n\n".join(chunk.content for chunk in chunks)
