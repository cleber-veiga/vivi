import operator
from langchain_core.messages import BaseMessage
from typing import NotRequired, TypedDict, Annotated, Sequence, Optional
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
    name: NotRequired[Optional[str]]
    email: NotRequired[Optional[str]]
    address: NotRequired[Optional[str]]
    cnpj: NotRequired[Optional[str]]
    corporate_reason: NotRequired[Optional[str]]
