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