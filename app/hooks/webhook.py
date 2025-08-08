import uuid
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from app.core.files import StorageManager
from app.services.audio import download_audio
from app.services.eleven import ElevenLabsClient
from settings import settings
from twilio.request_validator import RequestValidator
from app.base.base import BaseMessage
from app.base.schemas import MessagePayload
from app.db.database import async_session
from twilio.rest import Client
from fastapi import BackgroundTasks

router = APIRouter(prefix="/message", tags=["Messages"])

@router.post("")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
    payload=MessagePayload,
):

    signature = request.headers.get("X-Twilio-Signature", "")
    form_vars = await request.form()

    proto = request.headers.get("x-forwarded-proto", "https").lower()
    host = request.headers.get("host", "")
    path = request.url.path
    url = f"{proto}://{host}{path}"

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    is_valid = validator.validate(url, form_vars, signature)


    if not is_valid:
        return Response(status_code=403, content="Invalid signature")

    # 2) verifica se a mensagem tem mídia de áudio
    num_media = int(form_vars.get("NumMedia", 0))
    audio_url = None

    for i in range(num_media):
        media_type = form_vars.get(f"MediaContentType{i}", "")
        if media_type.startswith("audio"):
            audio_url = form_vars.get(f"MediaUrl{i}")
            break
    
    background_tasks.add_task(processo_lento_e_resposta, From, To, audio_url, Body)
    return Response(status_code=200, content="")

@router.post("/test")
async def receive_message_test(payload: MessagePayload):
    async with async_session() as session:
        agent = BaseMessage(request=payload, session=session)
        reply_text = await agent.handle()
    return {"reply_text": reply_text}

async def processo_lento_e_resposta(phone: str, to_phone: str, audio_url: str | None, body: str):
    payload = MessagePayload()
    payload.phone = phone.replace('whatsapp:+', '')

    try:
        if audio_url:
            audio_file = await download_audio(audio_url)

            eleven = ElevenLabsClient()
            transcript = await eleven.speech_to_text(audio_file)
            payload.message = transcript
        else:
            payload.message = body

        async with async_session() as session:
            agent = BaseMessage(request=payload, session=session)
            reply_text = await agent.handle()

        if audio_url:
            eleven = ElevenLabsClient()
            audio_response = await eleven.text_to_speech(reply_text)

            storage = StorageManager()
            storage_response = await storage.upload_bytes(
                file_type='audio',
                file_bytes=audio_response,
                filename=f"{payload.phone}_{uuid.uuid1()}_audio.mp3",
                content_type="audio/mpeg",
                is_public=True,
                fixed_url=True
            )

            # Envia resposta final via Twilio REST API
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                from_=to_phone,
                to=f'whatsapp:+{payload.phone}',
                body=reply_text,
                media_url=[storage_response["url"]] if storage_response["success"] else None
            )
        else:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                from_=to_phone,
                to=f'whatsapp:+{payload.phone}',
                body=reply_text
            )

    except Exception as e:
        print(f"❌ Erro ao processar e enviar resposta: {e}")