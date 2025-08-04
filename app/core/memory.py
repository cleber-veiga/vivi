from typing import List, Dict, Literal
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

RoleType = Literal["user", "assistant"]

class SimpleMemory:
    def __init__(self, memory_data: Dict = None):
        self.messages: List[Dict[str, str]] = []

        if memory_data and "messages" in memory_data:
            self.messages = memory_data["messages"]

    def add_message(self, role: RoleType, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return self.messages

    def to_dict(self) -> Dict[str, List[Dict[str, str]]]:
        return {"messages": self.messages}

    def clear(self) -> None:
        self.messages.clear()

    def message_converter(self, message_json):
        converted_messages = []
        for msg in message_json:
            if msg["role"] == "user":
                converted_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                converted_messages.append(AIMessage(content=msg["content"]))
            # pode ignorar outros tipos se não usar "system" ou "tool"
        return converted_messages