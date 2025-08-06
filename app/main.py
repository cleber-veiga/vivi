import os
from pathlib import Path
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
from settings import settings
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.hooks import webhook
from app.api import agent_routes, document_routes, auth_routes
from pyngrok import ngrok
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan handler: testa conexão com o banco e (opcionalmente) abre o túnel ngrok antes de iniciar a app.
    """
    # 1) Testa conexão com o banco de dados
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"Erro ao conectar com banco de dados: {e}")
        sys.exit(1)

    # 2) Se configurado para usar ngrok, abre o túnel uma vez
    if getattr(settings, "USE_NGROK", False) and not os.getenv("NGROK_TUNNEL_OPENED"):
        port = int(settings.SERVER_PORT)
        ngrok.set_auth_token(settings.NGROK_AUTH_TOKEN)
        tunnel = ngrok.connect(port, proto="http")

        print(f"🔥 API disponível em: {tunnel.public_url}")

        # Armazena no ambiente
        os.environ["NGROK_TUNNEL_OPENED"] = "1"
        os.environ["NGROK_PUBLIC_URL"] = tunnel.public_url  # <== Adicionado

    yield

BASE_DIR = Path(__file__).resolve().parent
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    raise RuntimeError(f"Não achei a pasta estática em {static_dir}")

# Criação da aplicação
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

# Serve tudo que estiver na pasta ./static
app.mount(
    "/static",
    StaticFiles(directory=str(static_dir)),
    name="static",
)

# Middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas API
app.include_router(agent_routes.router, prefix="/api")
app.include_router(document_routes.router, prefix="/api")
app.include_router(auth_routes.router)

# Rotas Webhooks
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
        reload=False
    )