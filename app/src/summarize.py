from typing import Dict, List
from langchain.chains.summarize import load_summarize_chain
from langchain_core.documents import Document

def format_conversation_for_summary(messages: List[Dict[str, str]]) -> str:
    return "\n".join(f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages)

async def summarize_conversation(messages: List[Dict[str, str]], llm) -> str:
    instruction = "Resuma a conversa abaixo em português de forma clara e objetiva:\n\n"
    text = instruction + format_conversation_for_summary(messages)
    doc = Document(page_content=text)
    chain = load_summarize_chain(llm, chain_type="stuff")  # você pode testar com 'map_reduce' se o texto for muito longo
    result = await chain.arun([doc])
    return result

def normalize_messages(messages: List[Dict]) -> List[Dict[str, str]]:
    """
    Garante que cada mensagem tenha 'role' e 'content' como strings.
    Remove mensagens inválidas ou vazias.
    """
    normalized = []
    for msg in messages:
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if role and content:
            normalized.append({"role": role, "content": content})
    return normalized

def safe_format_conversation(messages: List[Dict[str, str]]) -> str:
    """
    Formata a conversa para envio ao LLM, com papéis em português.
    """
    role_map = {"user": "Usuário", "assistant": "Assistente", "system": "Sistema"}
    lines = []
    for msg in messages:
        role_label = role_map.get(msg["role"], msg["role"].capitalize())
        content = msg["content"].replace("\n", " ").strip()
        lines.append(f"{role_label}: {content}")
    return "\n".join(lines)

async def summarize_conversation_temp(messages: List[Dict], llm) -> str:
    """
    Resume a conversa usando o LLM, com tratamento seguro do input.
    """
    instruction = "Resuma a conversa abaixo em português de forma clara e objetiva:\n\n"
    safe_messages = normalize_messages(messages['messages'])
    text = instruction + safe_format_conversation(safe_messages)
    doc = Document(page_content=text)
    chain = load_summarize_chain(llm, chain_type="stuff")
    result = await chain.arun([doc])
    return result