from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from google.cloud import storage
from starlette.responses import JSONResponse
from typing import Literal
import os
from app.utils.path_base import find_project_root
from datetime import timedelta

router = APIRouter(prefix="/files", tags=["Arquivos"])
BUCKET_NAME = "vivi-dev-bucket"

client = storage.Client()


@router.post("/upload/{file_type}", tags=["GCS Files"])
async def upload_file(
    file_type: Literal["audio", "video", "img"],
    file: UploadFile = File(...),
    is_public: bool = Query(default=False, description="Tornar arquivo público?"),
    fixed_url: bool = Query(default=False, description="Gerar URL fixa (pública) ou temporária?")
):
    try:
        blob_path = f"{file_type}/{file.filename}"
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(blob_path)

        # Envia o arquivo
        blob.upload_from_file(file.file, content_type=file.content_type)

        # Torna público, se solicitado
        if is_public:
            blob.acl.reload()
            blob.acl.all().grant_read()
            blob.acl.save()

        # Define a URL de retorno
        if is_public and fixed_url:
            url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}"
        else:
            url = blob.generate_signed_url(expiration=timedelta(minutes=15))

        return {
            "message": "Arquivo enviado com sucesso!",
            "url": url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar arquivo: {e}")


@router.get("/list/{file_type}", tags=["GCS Files"])
async def list_files(file_type: Literal["audio", "video", "img"]):
    try:
        bucket = client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix=f"{file_type}/")
        arquivos = [blob.name.split("/", 1)[1] for blob in blobs if "/" in blob.name]
        return {"arquivos": arquivos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos: {e}")


@router.delete("/delete/{file_type}/{filename}", tags=["GCS Files"])
async def delete_file(file_type: Literal["audio", "video", "img"], filename: str):
    try:
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"{file_type}/{filename}")

        if not blob.exists():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")

        blob.delete()
        return {"message": f"{filename} deletado com sucesso."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar arquivo: {e}")


@router.get("/url/{file_type}/{filename}", tags=["GCS Files"])
async def get_public_url(file_type: Literal["audio", "video", "img"], filename: str):
    blob = client.bucket(BUCKET_NAME).blob(f"{file_type}/{filename}")
    if not blob.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return {"url": blob.public_url}

