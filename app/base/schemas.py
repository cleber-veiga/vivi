import operator
from langchain_core.messages import BaseMessage
from typing import TypedDict, Annotated, Sequence, Optional
from pydantic import BaseModel

class MessagePayload(BaseModel):
    phone: str
    message: str

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    structured_response: Optional[dict]
    remaining_steps: int
    agent_scratchpad: list
    phone: str