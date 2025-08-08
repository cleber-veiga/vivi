from elevenlabs import ElevenLabs, save
from settings import settings
from io import BytesIO
from elevenlabs import PronunciationDictionaryVersionLocator


class ElevenLabsClient:
    def __init__(self, voice_id: str = "cVd39cx0VtXNC13y5Y7z"):
        self.client = ElevenLabs(api_key=settings.ELEVEN_LABS_API_KEY)
        self.voice_id = voice_id

    async def text_to_speech(self, text: str, model: str = "eleven_multilingual_v2") -> bytes:
        """
        Converte texto em áudio (TTS) e retorna os bytes do áudio.
        """
        try:

            voice_settings = {
                "stability": 0.4,
                "similarity_boost": 0.8,
                "style": 0.6,
                "use_speaker_boost": True,
                "speed": 1.2
            }

            audio_stream = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                output_format="mp3_44100_128",
                text=text,
                model_id=model,
                voice_settings=voice_settings,
                pronunciation_dictionary_locators=[
                    PronunciationDictionaryVersionLocator(
                        pronunciation_dictionary_id="w5LbqSAvPdPFb2cLyqBv",
                        version_id="2igwmKt9xTI1IIjqEhAZ"
                    )
                ]
            )

            audio = b"".join(chunk for chunk in audio_stream)
            return audio

        except Exception as e:
            print("❌ Erro durante a conversão de texto para áudio:")
            print(e)
            return b""  # ou retorne uma mensagem de erro conforme sua lógica

    async def speech_to_text(self, audio_file: BytesIO, model: str = "scribe_v1") -> str:
        """
        Converte áudio (em BytesIO) para texto (STT).
        """
        try:
            audio_file.seek(0)  # Garante que está no início

            transcript = self.client.speech_to_text.convert(
                file=audio_file,
                model_id=model,
                language_code="por"
            )

            return transcript.text

        except Exception as e:
            print(f"❌ Erro ao converter áudio para texto:{e}")
            return f"[Erro ao transcrever: {e}]"
