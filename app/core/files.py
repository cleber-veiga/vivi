from io import BytesIO
from google.cloud import storage
from typing import Literal
from datetime import timedelta

BUCKET_NAME = "vivi-dev-bucket"
client = storage.Client()

class StorageManager:
    def __init__(self):
        pass

    async def upload_bytes(
        self,
        file_type: Literal["audio", "video", "img"],
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        is_public: bool = False,
        fixed_url: bool = False
    ) -> dict:
        try:
            blob_path = f"{file_type}/{filename}"
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob(blob_path)

            # Envia o arquivo a partir de bytes
            file_obj = BytesIO(file_bytes)
            blob.upload_from_file(file_obj, content_type=content_type)

            if is_public and fixed_url:
                url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}"
            else:
                url = blob.generate_signed_url(expiration=timedelta(minutes=15))

            return {
                "success": True,
                "url": url
            }

        except Exception as e:
            print(f"[StorageManager] Erro ao enviar arquivo: {e}")
            return {
                "success": False,
                "url": ""
            }
