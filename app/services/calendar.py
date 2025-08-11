from datetime import datetime, timezone, timedelta
import pytz
import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from app.models import Agent, OAuthToken
from settings import settings

SKEW = timedelta(minutes=5)

def _aware_utc(dt):
    """Converte qualquer datetime para timezone-aware UTC (assumindo UTC se vier naive)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=timezone.utc)

def _mask_token(tok: str, show_start: int = 6, show_end: int = 6) -> str:
    if not tok:
        return "<empty>"
    if len(tok) <= show_start + show_end:
        return tok[:3] + "..."  # bem curtinho, só pra log
    return f"{tok[:show_start]}...{tok[-show_end:]}"

async def get_valid_google_credentials(session: AsyncSession, agent_id: int, force_refresh: bool = False) -> tuple[str, str]:
    """
    Recupera o token OAuth e SÓ RENOVA se estiver expirado (ou perto) usando um SKEW.
    Retorna: (access_token, calendar_id_ou_email)
    """
    print(f"[OAuth] Iniciando get_valid_google_credentials(agent_id={agent_id})")

    # ---------- Carrega Agent/Token ----------
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent: Agent | None = result.scalar_one_or_none()
    if not agent or not agent.oauth_token:
        print(f"[OAuth][ERRO] Agent não encontrado ou sem oauth_token (agent_id={agent_id})")
        raise ValueError("Agente não encontrado ou sem token vinculado")

    token_obj: OAuthToken = agent.oauth_token

    # ---------- Normaliza expiração e calcula SKEW ----------
    expires_at_raw = token_obj.expires_at
    expires_at = _aware_utc(expires_at_raw)
    now_utc = datetime.now(timezone.utc)
    consider_expired = (expires_at is None) or (expires_at - now_utc <= SKEW)

    print(f"[OAuth] user_email={token_obj.user_email}")
    print(f"[OAuth] token_type={token_obj.token_type}")
    print(f"[OAuth] token(antes)={_mask_token(token_obj.access_token)}")
    print(f"[OAuth] refresh_token(tem?){'sim' if bool(token_obj.refresh_token) else 'nao'}")
    print(f"[OAuth] expires_at_raw={expires_at_raw} | expires_at_utc={expires_at} | now_utc={now_utc} | consider_expired={consider_expired}")

    # ---------- Monta Credentials ----------
    scopes = token_obj.scope.split() if token_obj.scope else ["https://www.googleapis.com/auth/calendar.readonly"]
    token_uri = getattr(settings, "GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")
    expiry_naive = expires_at.replace(tzinfo=None) if expires_at else None  # evitar bug interno do google-auth

    print(f"[OAuth] scopes={scopes}")
    print(f"[OAuth] token_uri={token_uri}")

    creds = Credentials(
        token=token_obj.access_token,
        refresh_token=token_obj.refresh_token,
        token_uri=token_uri,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=scopes,
        expiry=expiry_naive,
    )

    # ---------- Decide e (talvez) renova ----------
    if consider_expired or force_refresh:
        print("[OAuth] Token expirado ou prestes a expirar. Renovando...")
        if not creds.refresh_token:
            print("[OAuth][ERRO] Sem refresh_token para renovar.")
            raise RuntimeError("Token inválido e sem refresh_token. Refaça o consentimento OAuth (offline).")

        try:
            creds.refresh(Request())
            print("[OAuth] Refresh OK.")
        except Exception as e:
            print(f"[OAuth][ERRO] Falha no refresh: {e}")
            raise RuntimeError(f"Falha ao renovar token OAuth: {e}") from e

        # ---------- Persiste novos dados ----------
        try:
            token_obj.access_token = creds.token
            if creds.expiry:
                token_obj.expires_at = creds.expiry.astimezone(timezone.utc)
            if creds.scopes:
                token_obj.scope = " ".join(creds.scopes)
            token_obj.token_type = "Bearer"
            await session.commit()

            print(f"[OAuth] Persistido no DB: token={_mask_token(token_obj.access_token)}, "
                  f"expires_at={token_obj.expires_at}, scopes={token_obj.scope}")
        except Exception as e:
            print(f"[OAuth][ERRO] Falha ao persistir no DB: {e}")
            raise
    else:
        print("[OAuth] Token ainda válido. Usando o do banco (sem refresh).")

    # ---------- Calendar ID ----------
    calendar_id = getattr(agent, "calendar_id", None) or token_obj.user_email or "primary"
    print(f"[OAuth] calendar_id={calendar_id}")
    print("[OAuth] get_valid_google_credentials concluído com sucesso.")

    # Nota: se não houve refresh, creds.token == token_obj.access_token original
    return creds.token, calendar_id


async def check_availability(session: AsyncSession, agent_id: int, data: str, hora: str, duracao_minutos: int = 60):
    """
    Verifica disponibilidade no Google Calendar. Se receber 401 (credencial inválida),
    força refresh do token, atualiza no banco e reenvia a requisição uma única vez.
    """
    def _post_freebusy(token: str, calendar_id: str, dt_inicio_iso: str, dt_fim_iso: str):
        url = "https://www.googleapis.com/calendar/v3/freeBusy"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "timeMin": dt_inicio_iso,
            "timeMax": dt_fim_iso,
            "items": [{"id": calendar_id}]
        }
        # timeout curto para não travar o fluxo; ajuste se necessário
        return requests.post(url, headers=headers, json=body, timeout=(5, 20))

    # 1) Monta janela no fuso correto
    tz = pytz.timezone("America/Sao_Paulo")
    dt_inicio = tz.localize(datetime.fromisoformat(f"{data}T{hora}"))
    dt_fim = dt_inicio + timedelta(minutes=duracao_minutos)

    # 2) Obtém credenciais válidas (sem forçar refresh)
    access_token, calendar_id = await get_valid_google_credentials(session, agent_id)

    # 3) Primeira tentativa
    response = _post_freebusy(access_token, calendar_id, dt_inicio.isoformat(), dt_fim.isoformat())

    # 4) Se 401, força refresh e tenta só mais uma vez
    if response.status_code == 401:
        # força refresh + persistência no banco
        access_token, calendar_id = await get_valid_google_credentials(session, agent_id, force_refresh=True)
        response = _post_freebusy(access_token, calendar_id, dt_inicio.isoformat(), dt_fim.isoformat())

    # 5) Trata respostas não-2xx
    if not (200 <= response.status_code < 300):
        try:
            result = response.json()
            msg = result.get("error", {}).get("message", response.text)
        except Exception:
            msg = response.text
        raise Exception(f"Erro ao consultar disponibilidade: {msg}")

    # 6) Sucesso
    result = response.json()
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

    dt_inicio = datetime.fromisoformat(f"{data}T{hora}")
    dt_fim = dt_inicio + timedelta(minutes=duracao_minutos)

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
