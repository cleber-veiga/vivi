from pydantic import BaseModel
from datetime import datetime

class AgentBase(BaseModel):
    name: str

class AgentCreate(AgentBase):
    pass

class AgentUpdate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True