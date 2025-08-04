import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.document import Document
from app.db.database import get_db
import tempfile
import shutil
from app.schemas.document import (
    DocumentUpdate, DocumentResponse
)
from app.src.chunk import ChunkProcessor
from app.src.parsers import CSVRead, DocxRead, MarkdownRead, PdfRead, TxtRead, XLSXRead
from pathlib import Path
from sqlalchemy import delete as sa_delete
from app.models.chunk import Chunk

ALLOWED_EXTENSIONS = {'.pdf', '.xlsx', '.docx', '.txt', '.csv', '.md'}

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/", response_model=DocumentResponse)
async def create_document(
    name: Optional[str] = Form(None),
    agent_id: int = Form(...),
    file: UploadFile = File(...),
    separator: Optional[str] = Form(","),
    sheet_name: Optional[str | int] = Form(0),
    session: AsyncSession = Depends(get_db)
):
    if file:
        ext = os.path.splitext(file.filename)[-1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Extensão de arquivo '{ext}' não suportada. Use: {', '.join(ALLOWED_EXTENSIONS)}"
            )
    
    # Mapear extensões para readers
    reads = {
        '.pdf': PdfRead(),
        '.docx': DocxRead(),
        '.txt': TxtRead(),
        '.md': MarkdownRead(),
        '.xlsx': XLSXRead(),
        '.csv': CSVRead()
    }

    # Salva temporariamente o arquivo
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        input_pdf_path = tmp.name

    # Executa a leitura baseada na extensão
    if ext == '.csv':
        result_convert = await reads[ext].read(input_pdf_path=Path(input_pdf_path), separator=separator)
    elif ext == '.xlsx':
        result_convert = await reads[ext].read(input_pdf_path=Path(input_pdf_path), sheet_name=sheet_name)
    else:
        result_convert = await reads[ext].read(input_pdf_path=Path(input_pdf_path))
    
    os.remove(input_pdf_path)

    doc = Document(name=name, agent_id=agent_id)
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    # Gera os chunks e salva
    chunker = ChunkProcessor(chunk_size=1000, chunk_overlap=100)
    chunks = chunker.generate_chunks(document_id=doc.id, content=result_convert)

    session.add_all(chunks)
    await session.commit()

    return doc
    

@router.get("/", response_model=list[DocumentResponse])
async def list_documents(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Document))
    return result.scalars().all()

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return doc

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(document_id: int, data: DocumentUpdate, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if data.name is not None:
        doc.name = data.name
    if data.agent_id is not None:
        doc.agent_id = data.agent_id

    await session.commit()
    await session.refresh(doc)
    return doc

@router.delete("/{document_id}")
async def delete_document(document_id: int, session: AsyncSession = Depends(get_db)):
    # Busca o documento
    result = await session.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Deleta os chunks relacionados
    await session.execute(
        sa_delete(Chunk).where(Chunk.document_id == document_id)
    )

    # Deleta o documento
    await session.delete(doc)
    await session.commit()

    return {"message": f"Documento (ID: {document_id}) e seus chunks foram removidos com sucesso."}

