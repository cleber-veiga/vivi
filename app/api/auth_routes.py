from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from fastapi import HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from app.db.database import get_db
from app.models import OAuthToken
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode
from settings import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

SCOPES = [
    "openid",  # <== necessário para retornar o id_token
    "email",   # <== necessário para garantir o e-mail no payload
    "profile", # <== opcional para nome/foto
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]

@router.get("/login")
async def auth_login():
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    return RedirectResponse(url)

@router.get("/callback")
async def auth_callback(code: str, session: AsyncSession = Depends(get_db)):
    token_url = settings.GOOGLE_TOKE_URI
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Erro ao obter token")

    token_data = response.json()

    # Recuperar e-mail do usuário via id_token
    id_token = token_data.get("id_token")
    user_info = requests.get(
        f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    ).json()
    user_email = user_info.get("email")

    if not user_email:
        raise HTTPException(status_code=400, detail="E-mail não encontrado")

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")  # pode ser None
    expires_in = int(token_data.get("expires_in", 3600))
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    # Salvar ou atualizar token no banco
    result = await session.execute(
        select(OAuthToken).where(OAuthToken.user_email == user_email)
    )
    token = result.scalar_one_or_none()
    if token:
        token.access_token = access_token
        token.refresh_token = refresh_token or token.refresh_token
        token.expires_at = expires_at
        token.scope = token_data.get("scope")
        token.token_type = token_data.get("token_type")
    else:
        token = OAuthToken(
            user_email=user_email,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scope=token_data.get("scope"),
            token_type=token_data.get("token_type"),
        )
        session.add(token)

    await session.commit()

    return JSONResponse(content={
        "mensagem": "Autenticação realizada com sucesso!",
        "user_email": user_email
    })

