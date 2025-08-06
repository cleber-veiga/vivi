from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from app.services.audio import download_audio
from app.src.transcribe import generate_audio_with_openai, transcribe_with_openai
from settings import settings
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from app.base.base import BaseMessage
from app.base.schemas import MessagePayload
from app.db.database import async_session
from app.utils.url_base import get_public_base_url

router = APIRouter(prefix="/message", tags=["Messages"])

@router.post("")
async def receive_message(
    request:    Request,
    From:       str = Form(...),  # número do usuário, ex: whatsapp:+5511987654321
    To:         str = Form(...),  # seu número do sandbox, ex: whatsapp:+14155238886
    Body:       str = Form(...),  # texto da mensagem
    MessageSid: str = Form(...),  # ID da mensagem no Twilio
    payload = MessagePayload
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
    
    # 3) transcreve o áudio (caso exista)
    if audio_url:
        try:
            audio_file = await download_audio(audio_url)

            transcript = await transcribe_with_openai(audio_file)
            payload.message = transcript
        except Exception:
            payload.message = "[Erro ao transcrever o áudio]"
    else:
        payload.message = Body
    
    # 4) define o remetente
    payload.phone = From.replace('whatsapp:+', '')

    # 5) chama o agente localmente
    try:
        async with async_session() as session:
            agent = BaseMessage(request=payload, session=session)
            # supondo que handle() retorne um objeto com .reply ou .text
            reply_text = await agent.handle()
            if audio_url:
                audio_response = await generate_audio_with_openai(text=reply_text, phone=payload.phone)
    except Exception:
        reply_text = "Ocorreu um erro interno. Tente novamente mais tarde."

    # 6) responde ao Twilio
    twiml = MessagingResponse()

    msg = twiml.message(reply_text)

    # se o áudio foi gerado, adiciona a mídia
    if audio_url:
        public_audio_url = f"{get_public_base_url()}/static/audio/{payload.phone}/audio.mp3"
        msg.media(public_audio_url)
    return Response(content=str(twiml), media_type="application/xml")

@router.post("/test")
async def receive_message_test(payload: MessagePayload):
    async with async_session() as session:
        agent = BaseMessage(request=payload, session=session)
        reply_text = await agent.handle()
    return {"reply_text": reply_text}