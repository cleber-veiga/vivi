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
async def estrutura_organizacional(query: str) -> str:
    """
    Ferramenta que retorna informações da Estrutura organizacional da Viasoft, como departamentos, produtos, parcerias e diferenciais estratégicos.
    Use sempre que o usuário solicitar esse tipo de informação

    Args:
        query (str): Pergunta reformulada com base na intenção apontada pelo usuário.

    Returns:
        str: Texto com os conhecimentos organizacionais.
    """
    async with async_session() as session:
        chunker = ChunkRetrive(session=session)
        retrieve = await chunker.retrieve(query=query, document_name="estrutura_organizacional")

    if not retrieve:
        return "Desculpe, não encontrei informações sobre a história ou missão da Viasoft no momento."

    return str(retrieve)

@tool
async def politicas_procedimentos(query: str) -> str:
    """
    Ferramenta que retorna informações das Políticas e Procedimentos da Viasoft
    Use sempre que o usuário solicitar esse tipo de informação

    Args:
        query (str): Pergunta reformulada com base na intenção apontada pelo usuário.

    Returns:
        str: Texto com os conhecimentos das Políticas e Procedimentos da Viasoft
    """
    async with async_session() as session:
        chunker = ChunkRetrive(session=session)
        retrieve = await chunker.retrieve(query=query, document_name="politicas_procedimentos")

    if not retrieve:
        return "Desculpe, não encontrei informações sobre a história ou missão da Viasoft no momento."

    return str(retrieve)


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
#   CAPTURAS
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@tool
async def capture_nome(phone: str, name: str) -> str:
    """
    Captura o nome do cliente e atualiza no banco de dados.
    Deve ser chamada sempre que o cliente passar seu nome na conversa.
    
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

@tool
async def capture_email(phone: str, email: str) -> str:
    """
    Captura o email do cliente e atualiza no banco de dados.
    Deve ser chamada sempre que o cliente passar seu email na conversa.
    
    Args:
        phone (str): número do telefone do lead `phone lead`
        email (str): email do cliente capturado
    """
    from app.db.database import async_session  # ajuste ao seu projeto
    async with async_session() as session:
        await MemoryService.upsert_memory(
            session=session,
            phone=phone,
            memory={},  # mantém a memória textual como está
            email=email
        )
    return f"Email '{email}' registrado com sucesso para o número {phone}."

@tool
async def capture_address(phone: str, address: str) -> str:
    """
    Captura o endereço do cliente e atualiza no banco de dados.
    Deve ser chamada sempre que o cliente passar seu endereço na conversa.
    
    Args:
        phone (str): número do telefone do lead `phone lead`
        address (str): endereço do cliente capturado
    """
    from app.db.database import async_session  # ajuste ao seu projeto
    async with async_session() as session:
        await MemoryService.upsert_memory(
            session=session,
            phone=phone,
            memory={},  # mantém a memória textual como está
            address=address
        )
    return f"Endereço '{address}' registrado com sucesso para o número {phone}."

@tool
async def capture_cnpj(phone: str, cnpj: str) -> str:
    """
    Captura o CNPJ do cliente e atualiza no banco de dados.
    Deve ser chamada sempre que o cliente passar seu CNPJ na conversa.
    
    Args:
        phone (str): número do telefone do lead `phone lead`
        cnpj (str): CNPJ do cliente capturado
    """
    from app.db.database import async_session  # ajuste ao seu projeto
    async with async_session() as session:
        await MemoryService.upsert_memory(
            session=session,
            phone=phone,
            memory={},  # mantém a memória textual como está
            cnpj=cnpj
        )
    return f"CNPJ '{cnpj}' registrado com sucesso para o número {phone}."

@tool
async def capture_corporate_reason(phone: str, corporate_reason: str) -> str:
    """
    Captura a razão social ou nome da empresa do cliente e atualiza no banco de dados.
    Deve ser chamada sempre que o cliente passar sua razão social ou nome da empresa na conversa.
    
    Args:
        phone (str): número do telefone do lead `phone lead`
        corporate_reason (str): razão social ou nome da empresa do cliente capturado
    """
    from app.db.database import async_session  # ajuste ao seu projeto
    async with async_session() as session:
        await MemoryService.upsert_memory(
            session=session,
            phone=phone,
            memory={},  # mantém a memória textual como está
            corporate_reason=corporate_reason
        )
    return f"Razão Social '{corporate_reason}' registrado com sucesso para o número {phone}."