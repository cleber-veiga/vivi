import os
from uuid import uuid4
from openai import OpenAI
from io import BytesIO
from settings import settings


client = OpenAI(api_key=settings.OPENAI_API_KEY)

async def transcribe_with_openai(audio_file: BytesIO) -> str:
    print("[transcribe_with_openai] Iniciando transcrição com novo client da OpenAI")

    try:
        audio_file.seek(0)
        audio_file.name = "audio.ogg"

        # Nova API de transcrição com OpenAI >= 1.0
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )

        texto = transcript.strip()
        print(f"[transcribe_with_openai] Transcrição concluída: {texto[:100]}...")
        return texto if texto else "[Sem conteúdo transcrito]"

    except Exception as e:
        print(f"[transcribe_with_openai] Erro durante transcrição: {e}")
        return "[Erro ao transcrever com OpenAI]"

async def generate_audio_with_openai(text: str, phone: str, filename: str = "audio.mp3") -> str:
    """
    Gera um áudio usando a voz shimmer da OpenAI e salva em ./static/{user_id}/{filename}
    
    Args:
        texto (str): Texto a ser convertido em fala.
        user_id (str): Identificador único do usuário.
        filename (str): Nome do arquivo MP3 (padrão: audio.mp3)

    Returns:
        str: Caminho absoluto do arquivo salvo.
    """
    try:
        
        from app.base.prompt import AUDIO_INSTRUCTION
        # Caminho do diretório de destino
        filename = f"audio_{uuid4().hex}.mp3"
        destination_folder = os.path.join("static", "audio", phone)
        os.makedirs(destination_folder, exist_ok=True)

        full_path = os.path.join(destination_folder, filename)

        audio = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="shimmer",
            input=text,
            instructions=AUDIO_INSTRUCTION
        )

        with open(full_path, "wb") as f:
            f.write(audio.content)

        return full_path
    
    except Exception as e:
        print(f"Erro ao gerar ou salvar o áudio: {e}")
        return None