import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
from settings import settings
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.hooks import webhook
from app.api.agent_routes import router as agent_routes
from app.api.document_routes import router as document_routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        yield
    except Exception as e:
        print(f"Erro ao conectar com banco de dados: {e}")
        sys.exit(1)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas API
app.include_router(agent_routes, prefix="/api")
app.include_router(document_routes, prefix="/api")

# Rotas Webhooks
app.include_router(webhook.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", proxy_headers=True)