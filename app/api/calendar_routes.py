# app/api/calendar.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.calendar import check_availability, schedule_event  # ajuste o import p/ o arquivo onde estão suas funcs

router = APIRouter(prefix="/calendar", tags=["calendar"])

class CheckAvailabilityBody(BaseModel):
    data: str = Field(..., description="Data no formato YYYY-MM-DD")
    hora: str = Field(..., description="Hora no formato HH:MM (24h)")
    duracao_minutos: int = Field(60, ge=1, le=24*60)

class ScheduleEventBody(BaseModel):
    data: str = Field(..., description="Data no formato YYYY-MM-DD")
    hora: str = Field(..., description="Hora no formato HH:MM (24h)")
    cliente: str = Field(..., min_length=1)
    assunto: str = Field("", description="Assunto opcional")
    duracao_minutos: int = Field(60, ge=1, le=24*60)
    email_convidado: EmailStr | None = None

@router.post("/{agent_id}/check")
async def check_route(
    agent_id: int,
    body: CheckAvailabilityBody,
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await check_availability(
            session=session,
            agent_id=agent_id,
            data=body.data,
            hora=body.hora,
            duracao_minutos=body.duracao_minutos,
        )
        return result
    except Exception as e:
        # Logue e detalhe se quiser
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{agent_id}/schedule")
async def schedule_route(
    agent_id: int,
    body: ScheduleEventBody,
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await schedule_event(
            session=session,
            agent_id=agent_id,
            data=body.data,
            hora=body.hora,
            cliente=body.cliente,
            assunto=body.assunto,
            duracao_minutos=body.duracao_minutos,
            email_convidado=body.email_convidado,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
