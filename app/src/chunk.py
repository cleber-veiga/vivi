from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.chunk import Chunk
from app.models.document import Document
from sqlalchemy import select
from app.src.embedding import EmbeddingProcessor
from sqlalchemy.ext.asyncio import AsyncSession

class ChunkProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 50):
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

class ChunkRetrieve:
    def __init__(self, session: AsyncSession):
        self.embedding = EmbeddingProcessor()
        self.session = session

    async def retrieve(self, query: str, document_name: str = "") -> List[Chunk]:
        # 1) Gera o vetor da consulta
        query_vector = self.embedding.embed_openai([query])[0]

        # 2) Monta a consulta SQL
        if document_name:
            stmt = (
                select(Chunk)
                .join(Document, Chunk.document_id == Document.id)
                .where(Document.name == document_name)
                .order_by(Chunk.embedding.l2_distance(query_vector))
                .limit(3)
            )
        else:
            stmt = (
                select(Chunk)
                .order_by(Chunk.embedding.l2_distance(query_vector))
                .limit(3)
            )

        # 3) Executa
        results = await self.session.execute(stmt)
        chunks: List[Chunk] = results.scalars().all()

        if not chunks:
            # você pode lançar exceção ou apenas logar
            print("[⚠️ AVISO] Nenhum chunk encontrado para os critérios informados.")

        return chunks
