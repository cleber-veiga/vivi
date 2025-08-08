from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.agent import Agent
from app.models.auth import OAuthToken
from app.db.database import get_db
from app.schemas.agent import AgentCreate, AgentResponse, AgentTokenLinkRequest

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.post("/", response_model=AgentResponse)
async def create_agent(agent: AgentCreate, session: AsyncSession = Depends(get_db)):
    new = Agent(name=agent.name)
    session.add(new)
    await session.commit()
    await session.refresh(new)
    return new

@router.get("/", response_model=list[AgentResponse])
async def list_agents(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Agent))
    return result.scalars().all()

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent não encontrado")
    return agent

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, data: AgentCreate, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent não encontrado")
    agent.name = data.name
    await session.commit()
    await session.refresh(agent)
    return agent

@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent não encontrado")
    await session.delete(agent)
    await session.commit()
    return {"message": "Agent removido com sucesso"}

@router.post("/{agent_id}/link")
@router.post("/{agent_id}/link")
async def vincular_token_ao_agente(
    agent_id: int,
    data: AgentTokenLinkRequest,
    session: AsyncSession = Depends(get_db)
):
    user_email = data.user_email
    
    result = await session.execute(
        select(OAuthToken).where(OAuthToken.user_email == user_email)
    )
    token = result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Token não encontrado para este e-mail")

    result = await session.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    agent.oauth_token_id = token.id
    await session.commit()

    return {"mensagem": f"Token do e-mail {user_email} vinculado ao agente {agent.name}."}
