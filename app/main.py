import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.base.summarize import generate_response_with_summary
from app.services.memory import record_llm_followup_like_previous
from settings import settings
from app.db.database import engine, async_session
from app.hooks import webhook
from app.api import agent_routes, document_routes, auth_routes, static_routes, calendar_routes

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from twilio.rest import Client
from anyio import to_thread
try:
    # opcional: só use ngrok em dev, controlado por env
    from pyngrok import ngrok
except Exception:
    ngrok = None

# === IMPORTS DO SEU FOLLOW-UP ===
# Ajuste o caminho conforme criou o serviço na dica anterior
from app.services.followup import FollowUpService


# --------- JOB ASSÍNCRONO DE FOLLOW-UP ----------
async def check_and_nudge_users():
    """
    Seleciona contatos cuja última interação foi da IA, não concluíram agendamento
    e já fazem >=10min sem resposta do usuário. Envia uma mensagem de retomada
    e incrementa a contagem de tentativas.
    """
    async with async_session() as session:
        rows = await FollowUpService.candidates(session)
        if not rows:
            return

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        for st in rows:
            try:
                # Gera a mensagem com base no resumo da conversa
                response = await generate_response_with_summary(session, st.phone)
                response = (response or "").strip() or \
                           "Posso te ajudar a retomar de onde paramos? 🙂"

                # Envia via Twilio sem bloquear o event loop
                client.messages.create(
                    from_=settings.TWILIO_WHATSAPP_FROM,
                    to=f'whatsapp:+{st.phone}',
                    body=response
                )
                
                await record_llm_followup_like_previous(session, st.phone, response)
                # Registra a tentativa de follow-up (contagem + timestamp)
                await FollowUpService.mark_followup_attempt(session, st.phone)

            except Exception as e:
                # loga e segue pros próximos
                print(f"[followup] erro ao enviar para {st.phone}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    - Testa conexão com o banco
    - Abre túnel ngrok (se habilitado)
    - Inicializa e inicia o scheduler
    - Finaliza o scheduler no shutdown
    """
    # 1) Banco
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"Erro ao conectar com banco de dados: {e}")
        sys.exit(1)

    # 2) ngrok opcional
    if getattr(settings, "USE_NGROK", False) and not os.getenv("NGROK_TUNNEL_OPENED"):
        if ngrok is None:
            print("[NGROK] pyngrok não disponível. Pulei abertura de túnel.")
        else:
            try:
                port = int(settings.SERVER_PORT)
                ngrok.set_auth_token(settings.NGROK_AUTH_TOKEN)
                tunnel = ngrok.connect(port, proto="http")
                print(f"🔥 API disponível em: {tunnel.public_url}")
                os.environ["NGROK_TUNNEL_OPENED"] = "1"
                os.environ["NGROK_PUBLIC_URL"] = tunnel.public_url
            except Exception as e:
                print(f"[NGROK] falha ao abrir túnel: {e}")

    # 3) Scheduler
    scheduler = AsyncIOScheduler(timezone=str(getattr(settings, "TZ", "UTC")))
    # roda a cada 1 minuto
    scheduler.add_job(check_and_nudge_users, "interval", minutes=1, id="followup_nudger", coalesce=True, max_instances=1)
    scheduler.start()
    print("[scheduler] iniciado")

    try:
        yield
    finally:
        # shutdown ordenado
        try:
            scheduler.shutdown(wait=False)
            print("[scheduler] finalizado")
        except Exception:
            pass


# --------- STATIC ---------
BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
for subfolder in ["audio", "video", "img"]:
    (static_dir / subfolder).mkdir(parents=True, exist_ok=True)

# --------- APP ---------
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas API
app.include_router(agent_routes.router, prefix="/api")
app.include_router(document_routes.router, prefix="/api")
app.include_router(static_routes.router, prefix="/api")
app.include_router(calendar_routes.router, prefix="/api")
app.include_router(auth_routes.router)

# Webhooks
app.include_router(webhook.router, prefix="/webhook")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(settings.SERVER_PORT),
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
        reload=False,
    )
