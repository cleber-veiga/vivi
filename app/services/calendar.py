import datetime
import requests
from sqlalchemy import select
from app.models import Agent, OAuthToken
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

async def check_availability(session: AsyncSession, agent_id: int, data: str, hora: str, duracao_minutos: int = 60):
    # Busca agente e token
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent or not agent.oauth_token:
        raise ValueError("Agente não encontrado ou sem token vinculado")

    access_token = agent.oauth_token.access_token
    calendar_id = agent.oauth_token.user_email

    # Constrói janela de tempo
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

    busy = result["calendars"][calendar_id]["busy"]
    if busy:
        return {"disponivel": False, "mensagem": "Horário indisponível"}
    else:
        return {"disponivel": True, "mensagem": "Horário disponível"}

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
    # Busca agente e token
    result = await session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent or not agent.oauth_token:
        raise ValueError("Agente não encontrado ou sem token vinculado")

    access_token = agent.oauth_token.access_token
    calendar_id = agent.oauth_token.user_email

    # Constrói horário do evento
    dt_inicio = datetime.datetime.fromisoformat(f"{data}T{hora}")
    dt_fim = dt_inicio + datetime.timedelta(minutes=duracao_minutos)

    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    evento = {
        "summary": f"Agendamento com {cliente} - {assunto}",
        "description": "",
        "start": {
            "dateTime": dt_inicio.isoformat(),
            "timeZone": "America/Sao_Paulo"
        },
        "end": {
            "dateTime": dt_fim.isoformat(),
            "timeZone": "America/Sao_Paulo"
        }
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
