from langchain.tools import tool
from app.base.schemas import AgentState
from app.db.database import async_session
from app.services.memory import MemoryService
from app.src.chunk import ChunkRetrive

@tool
def saudacao_inicial() -> str:
    """Ferramenta que trará informações importantes de comportamento ao realizar saudações em inicios de conversa com novos leads
    """
    return """
“Ooi! Eu sou a Vivi. Estou aqui pra fazer valer cada segundo do seu tempo e interesse pela VIASOFT. Como posso te chamar?”
"""

@tool
async def historia_missao_valores(query: str) -> str:
    """
    Ferramenta que retorna informações institucionais da Viasoft, como história, missão e valores.
    Use sempre que o usuário solicitar quem é a empresa ou informações culturais da organização.

    Args:
        query (str): Pergunta reformulada com base na intenção do usuário.

    Returns:
        str: Texto com os conhecimentos institucionais.
    """
    async with async_session() as session:
        chunker = ChunkRetrive(session=session)
        retrieve = await chunker.retrieve(query=query, document_name="historia_missao_valores")

    if not retrieve:
        return "Desculpe, não encontrei informações sobre a história ou missão da Viasoft no momento."

    return str(retrieve)

@tool
async def capture_nome(phone: str, name: str) -> str:
    """
    Captura o nome do cliente e atualiza no banco de dados.
    Deve ser chamada sempre que o cliente disser seu nome na conversa.
    
    Args:
        phone (str): número do telefone do lead `phone lead`
        name (str): nome do cliente capturado
    """
    from app.db.database import async_session  # ajuste ao seu projeto
    async with async_session() as session:
        await MemoryService.upsert_memory(
            session=session,
            phone=phone,
            memory={},  # mantém a memória textual como está
            name=name
        )
    return f"Nome '{name}' registrado com sucesso para o número {phone}."