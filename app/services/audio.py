import aiohttp
from io import BytesIO
from base64 import b64encode
from settings import settings

async def download_audio(url: str) -> BytesIO | None:
    try:
        # Autenticação básica para a API do Twilio
        auth = aiohttp.BasicAuth(
            login=settings.TWILIO_ACCOUNT_SID,
            password=settings.TWILIO_AUTH_TOKEN
        )

        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    audio_bytes = await response.read()

                    audio_file = BytesIO(audio_bytes)
                    audio_file.name = "audio.ogg"
                    return audio_file
                else:
                    print(f"[download_audio] Erro HTTP: status {response.status}")
    except Exception as e:
        print(f"[download_audio] Exceção capturada: {e}")

    return None