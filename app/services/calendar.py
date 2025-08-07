import datetime
import pytz
import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from app.models import Agent, OAuthToken
from settings import settings

async def get_valid_google_credentials(session: AsyncSession, agent_id: int) -> tuple[str, str]:
    """
    Recupera e renova o token OAuth se necessário.
    Retorna: (access_token, calendar_id)
    """
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent or not agent.oauth_token:
        raise ValueError("Agente não encontrado ou sem token vinculado")

    token_obj: OAuthToken = agent.oauth_token

    creds = Credentials(
        token=token_obj.access_token,
        refresh_token=token_obj.refresh_token,
        token_uri=settings.GOOGLE_TOKE_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Atualiza o access_token no banco de dados
            token_obj.access_token = creds.token
            await session.commit()
        except Exception as e:
            raise RuntimeError(f"Falha ao renovar token OAuth: {str(e)}")

    return creds.token, token_obj.user_email

async def check_availability(session: AsyncSession, agent_id: int, data: str, hora: str, duracao_minutos: int = 60):
    access_token, calendar_id = await get_valid_google_credentials(session, agent_id)

    tz = pytz.timezone("America/Sao_Paulo")
    dt_inicio = tz.localize(datetime.datetime.fromisoformat(f"{data}T{hora}"))
    dt_fim = dt_inicio + datetime.timedelta(minutes=duracao_minutos)

    url = "https://www.googleapis.com/calendar/v3/freeBusy"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    body = {
        "timeMin": dt_inicio.isoformat(),
        "timeMax": dt_fim.isoformat(),
        "items": [{"id": calendar_id}]
    }

    response = requests.post(url, headers=headers, json=body)
    result = response.json()

    if response.status_code != 200:
        raise Exception(f"Erro ao consultar disponibilidade: {result.get('error', {}).get('message', response.text)}")

    busy = result["calendars"][calendar_id]["busy"]
    return {
        "disponivel": not bool(busy),
        "mensagem": "Horário disponível" if not busy else "Horário indisponível"
    }

async def schedule_event(
    session: AsyncSession,
    agent_id: int,
    data: str,
    hora: str,
    cliente: str,
    assunto: str = "",
    duracao_minutos: int = 60,
    email_convidado: str = None
):
    access_token, calendar_id = await get_valid_google_credentials(session, agent_id)

    dt_inicio = datetime.datetime.fromisoformat(f"{data}T{hora}")
    dt_fim = dt_inicio + datetime.timedelta(minutes=duracao_minutos)

    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    evento = {
        "summary": f"Agendamento com {cliente} - {assunto}",
        "start": {"dateTime": dt_inicio.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": dt_fim.isoformat(), "timeZone": "America/Sao_Paulo"},
    }

    if email_convidado:
        evento["attendees"] = [{"email": email_convidado}]

    response = requests.post(url, headers=headers, json=evento)

    if response.status_code != 200:
        raise Exception(f"Erro ao criar evento: {response.text}")

    return {
        "status": "sucesso",
        "mensagem": f"Evento agendado para {cliente} em {data} às {hora}.",
        "evento": response.json()
    }
