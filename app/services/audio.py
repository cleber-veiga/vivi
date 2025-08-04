import aiohttp
from io import BytesIO
from base64 import b64encode
from settings import settings

async def download_audio(url: str) -> BytesIO | None:
    print(f"[download_audio] Iniciando download do áudio: {url}")
    
    try:
        # Autenticação básica para a API do Twilio
        auth = aiohttp.BasicAuth(
            login=settings.TWILIO_ACCOUNT_SID,
            password=settings.TWILIO_AUTH_TOKEN
        )

        async with aiohttp.ClientSession(auth=auth) as session:
            print("[download_audio] Sessão aiohttp com auth iniciada")
            
            async with session.get(url, allow_redirects=True) as response:
                print(f"[download_audio] Status da resposta: {response.status}")
                
                if response.status == 200:
                    audio_bytes = await response.read()
                    print(f"[download_audio] Tamanho do áudio recebido: {len(audio_bytes)} bytes")

                    audio_file = BytesIO(audio_bytes)
                    audio_file.name = "audio.ogg"
                    print("[download_audio] BytesIO criado com sucesso")
                    return audio_file
                else:
                    print(f"[download_audio] Erro HTTP: status {response.status}")
    except Exception as e:
        print(f"[download_audio] Exceção capturada: {e}")

    print("[download_audio] Retornando None")
    return None