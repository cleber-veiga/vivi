import uuid
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
from app.core.files import StorageManager
from app.services.audio import download_audio
from app.services.eleven import ElevenLabsClient
from app.services.followup import FollowUpService
from app.services.memory import MemoryService
from app.utils.url_videos import get_url_video_by_id
from app.utils.utils import split_text_by_video
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

    try:
        phone_raw = From
        phone_clean = (phone_raw or "").replace('whatsapp:+','')
        if phone_clean:
            async with async_session() as session:
                await FollowUpService.mark_user_msg(session, phone_clean)
    except Exception as e:
        # não bloqueia o fluxo do webhook
        print(f"[followup] falha ao marcar user msg: {e}")
    
    background_tasks.add_task(processo_lento_e_resposta, From, To, audio_url, Body)
    return Response(status_code=200, content="")

@router.post("/test")
async def receive_message_test(payload: MessagePayload):

    if payload.message == "Reset":
        async with async_session() as session:
            delete_message = await MemoryService.delete_memory_by_phone(session=session,phone=payload.phone)
        if delete_message == True:
            return {"reply_text": "Pronto, o histórico foi resetado. A próxima interação será considerada a primeira"}

    async with async_session() as session:
        agent = BaseMessage(request=payload, session=session)
        reply_text = await agent.handle()
    return {"reply_text": reply_text}

async def processo_lento_e_resposta(phone: str, to_phone: str, audio_url: str | None, body: str):
    payload = MessagePayload()
    payload.phone = phone.replace('whatsapp:+', '')
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    list_video = []

    if body.lower() in ['reset','reiniciar','remover']:
        async with async_session() as session:
            delete_message = await MemoryService.delete_memory_by_phone(session=session,phone=payload.phone)
            delete_fallowup = await FollowUpService.delete_fllow_up_by_phone(session=session,phone=payload.phone)
        if delete_message and delete_fallowup:
            client.messages.create(
                from_=to_phone,
                to=f'whatsapp:+{payload.phone}',
                body="Pronto, o histórico foi removido. A próxima interação será considerada a primeira"
            )
            return
        
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
            
            client.messages.create(
                from_=to_phone,
                to=f'whatsapp:+{payload.phone}',
                body=reply_text,
                media_url=[storage_response["url"]] if storage_response["success"] else None
            )

            try:
                async with async_session() as session:
                    await FollowUpService.mark_ai_reply(session, payload.phone, schedule_done=False)
            except Exception as e:
                print(f"[followup] falha ao marcar ai (audio): {e}")
        else:

            result = split_text_by_video(reply_text)  # -> (before, token_dict, after) ou (before, key, after)
            if not result:
                client.messages.create(
                    from_=to_phone,
                    to=f'whatsapp:+{payload.phone}',
                    body=reply_text
                )
                
                # --- IA FOI A ÚLTIMA A ENVIAR (texto simples) ---
                try:
                    async with async_session() as session:
                        await FollowUpService.mark_ai_reply(session, payload.phone, schedule_done=False)
                except Exception as e:
                    print(f"[followup] falha ao marcar ai (texto simples): {e}")
                return

            before, video_token, after = result

            # Envia "before" se existir
            if before and before.strip():
                client.messages.create(
                    from_=to_phone,
                    to=f'whatsapp:+{payload.phone}',
                    body=before
                )

            # Resolve vídeo (url/caption)
            url_video = None
            caption = None

            if isinstance(video_token, dict):
                # Ex: {"key": "...", "url": "...", "caption": "..."}
                key = video_token.get("key")
                url_video = video_token.get("url") or (get_url_video_by_id(key) if key else None)
                caption = video_token.get("caption") or ""
            else:
                # Backward-compatible: token é só a key
                key = video_token
                url_video = get_url_video_by_id(key)
                caption = ""

            if url_video:
                client.messages.create(
                    from_=to_phone,
                    to=f'whatsapp:+{payload.phone}',
                    body=caption,
                    media_url=[url_video]
                )
                async with async_session() as session:
                    await MemoryService.add_video_enviado(
                        session=session,
                        phone=payload.phone,
                        video=key
                    )

            # Envia "after" se existir
            if after and after.strip():
                client.messages.create(
                    from_=to_phone,
                    to=f'whatsapp:+{payload.phone}',
                    body=after
                )
                # --- IA FOI A ÚLTIMA A ENVIAR (ramo com vídeo/partes) ---
                try:
                    async with async_session() as session:
                        await FollowUpService.mark_ai_reply(session, payload.phone, schedule_done=False)
                except Exception as e:
                 print(f"[followup] falha ao marcar ai (video/partes): {e}")

    except Exception as e:
        print(f"❌ Erro ao processar e enviar resposta: {e}")