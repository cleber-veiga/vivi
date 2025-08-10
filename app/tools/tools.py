from typing import Any, Dict, List, Optional
from langchain.tools import tool
from app.base.schemas import AgentState
from app.db.database import async_session
from app.services.calendar import check_availability, schedule_event
from app.services.memory import MemoryService
from app.src.chunk import ChunkRetrieve
from langchain.tools import tool
from app.db.database import async_session
from datetime import datetime, timedelta, time
import requests
from sqlalchemy import select
from app.models import Agent, OAuthToken

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
#  FERRAMENTA DE INFORMAÇÃO
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@tool
async def semantic_documentary_search(queries: Dict[str, str]) -> str:
    """
    Consulta documentos internos da Viasoft com base em busca semântica.
    Consulta múltiplos documentos internos da Viasoft com base em busca semântica.
    Permite usar uma pergunta (query) diferente para cada documento, e executa buscas simultâneas de forma segura.
    Sempre avalie as informações que quer buscar com base na pergunta do usuario;
    IMPORTANTE -> SEMPRE USE NO MÁXIMO 4 FERRAMENTAS
    
    Types:
        "info_..." -> Documentos que iniciam com isso são documentos com ricos em informações, conteúdo, dados
        "exemp_..." -> Documentos que iniciam com isso são documentos que possuem exemplos práticos e reais de diversas situações

    Documents:
        - "info_estrutura" -> Use quando precisar de informações da Estrutura organizacional da Viasoft, como departamentos, produtos, parcerias e diferenciais estratégicos.
        - "info_etica" -> Use quando precisar de conteúdo sobre o de Código de Ética da Viasoft.
        - "info_implantacao" ->  Use quando precisar Informações do funcionamento da Implantação de software da Viasoft.
        - "info_produto_funcion" -> User quando precisar de conteúdo sobre as principais funcionalidades do sistema Construshow
        - "info_swot" -> Use quando precisar ver análises de fraquezas dos concorrentes e como o construshow se sai melhor do que eles
        - "info_ciclo_mel" -> Use quando precisar saber como funciona o fluxo de melhoria e desenvolvimento do produto construshow
        - "info_politicas" -> Use quando precisar de conteúdo das Políticas e Procedimentos Internos da Viasoft com base em perguntas específicas.
        - "info_historia" -> Use quando precisar de informações institucionais da Viasoft, como história, missão e valores.
        - "info_escopo_esperado" -> Use quando precisar de informações sobre quais clientes atendementos
        - "info_suporte_viasoft" -> Use quando precisar de informações de como funciona o suporte da Viasoft
        - "info_outros_produtos" -> Use quando precisar de detalhamentos sobre outros produtos da Viasoft, excluindo o Construshow, focando em suas funcionalidades e benefícios para diversos setores.
        - "info_tecnico_constru" -> Use para obter informações técnicas do sistema Construshow, incluindo linguagem de desenvolvimento (Delphi Berlin com componentes TMS), banco de dados (Oracle 19c ou superior, com destaque para Oracle Cloud e Exadata) e requisitos mínimos de infraestrutura para diferentes volumes de usuários.
        - "info_cases_sucesso" -> Use sempre que precisar saber alguns clientes que já usam construshow ou saber de cases de sucesso, use para criar valor ao produto
        - "info_manifesto_ceo" -> Manifesto do CEO, que contem o olhar do CEO sobre os fatores que compõem o verdadeiro poder da Viasoft
        - "info_reajuste_contratos" -> Informações de como funciona os reajustes de contrato
        - "info_eugenius" -> Informações do Eugenius, uma IA mentora para líderes, detalhando seus perfis de usuário, dores que resolve, jornada de compra, proposta de valor por setor, análise SWOT e funcionalidades
        - "exemp_rapport" -> Exemplos para criar rapport e conexão com clientes
        - "exemp_objecoes" -> Exemplos para superar objeções do cliente
        - "exemp_neg_preco" -> Exemplos de como agir mencionar preço, taxas, reajustes de contrato e coisas do tipo
        - "exemp_resposta_concorrente" -> Exemplos de respostas quando usuário mencionar sistemas concorrentes ao Construshow
        
    Args:
        queries (Dict[str, str]): Dicionário onde:
            - A chave é o nome do documento.
            - O valor é a pergunta associada a esse documento.
            
            Exemplo:
            {{
                "info_etica": "Como funciona o código de conduta?",
                "info_implantacao": "Qual é o passo a passo da implantação do sistema?"
            }}

    Returns:
        str: Resumo consolidado com os trechos mais relevantes de cada documento consultado.
    """
    from asyncio import gather

    # Definindo uma função que encapsula a sessão por tarefa
    async def retrieve_from_doc(doc_name: str, query: str):
        async with async_session() as session:
            chunker = ChunkRetrieve(session=session)
            return await chunker.retrieve(query=query, document_name=doc_name)

    # Preparando tarefas individuais com sessões independentes
    tasks = [retrieve_from_doc(doc, query) for doc, query in queries.items()]
    results = await gather(*tasks)

    # Formatando os resultados
    response_parts = []
    for (doc_name, query), chunks in zip(queries.items(), results):
        if not chunks:
            response_parts.append(f"❌ Nenhuma informação encontrada em **{doc_name}** para: _{query}_")
            continue

        doc_header = f"## 📘 Resultados para `{doc_name}` — Pergunta: _{query}_"
        parts = []
        for c in chunks:
            header = f"### {c.section_title} — {c.chunk_position} — {c.token_count} tokens"
            parts.append(f"{header}\n\n{c.content}")
        response_parts.append(f"{doc_header}\n\n" + "\n\n".join(parts))

    return "\n\n---\n\n".join(response_parts)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
#  FERRAMENTA DE CAPTURA
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@tool
async def capture_lead_data(phone: str, data: Dict[str, Any]) -> Dict[str, str]:
    """
    Captura dados do cliente e atualiza no banco de dados.
    Deve ser chamada sempre que o cliente fornecer algum dos argumentos dentro de data.
    
    Args:
        phone (str): número do telefone do lead.
        data (Dict[str, Any]): dicionário com campos a serem atualizados. Pode conter:
            - name (str) -> Nome do Lead
            - email (str) -> Email do Lead (NUNCA INVENTE)
            - cnpj (str) -> CNPJ do lead
            - corporate_reason (str) -> Razão Social do Lead
            - uf (str) -> UF do Lead
            - cidade (str) -> Cidade do Lead
            - quantidade_usuarios (int) -> Quantidade de usuários da empresa (SOMENTE O NUMERO!)
            - sistema_atual (str) -> Nome do sistema que o cliente usa atualmente
            - desafios (str) -> Desafios, dores, reclamações que o cliente apontar na sua pergunta, se houver mais de um separar por vírgula

    Returns:
        Dict[str, str]: dados atualizados com sucesso.
    """
    from app.db.database import async_session  # ajuste ao seu projeto
    
    async with async_session() as session:
        await MemoryService.upsert_memory(
            session=session,
            phone=phone,
            memory={},  # mantém a memória textual como está
            **data  # aplica os dados dinamicamente
        )
        if "desafios" in data:
            for item in (x.strip() for x in data["desafios"].split(",") if x.strip()):
                await MemoryService.add_desafio_cliente(
                    session=session,
                    phone=phone,
                    desafio=item
                )

    return data

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
#  FERRAMENTAS EXTERNAS
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@tool
async def serv_agenda_disp(data: Optional[str] = None, hora: Optional[str] = None) -> list:
    """
    Consulta os horários disponíveis do agente nos próximos 10 dias (exceto sábados e domingos),
    durante o horário comercial: das 08:00 às 12:00 e das 13:30 às 18:00.

    Se o cliente fornecer uma data e hora específicas, será feita a verificação.
    Se estiver ocupado, serão sugeridos horários alternativos.
    Se nada for informado, retorna todos os horários disponíveis nos próximos 10 dias.

    Args:
        data (str, opcional): Data desejada no formato YYYY-MM-DD
        hora (str, opcional): Hora desejada no formato HH:MM

    Returns:
        Lista de horários disponíveis ou sugestão alternativa
    """
    agent_id = 1  # fixo por enquanto
    async with async_session() as session:
        agora = datetime.now()
        horarios_disponiveis = []

        # Caso data e hora sejam fornecidos, verificar diretamente
        if data and hora:
            disponibilidade = await check_availability(
                session=session,
                agent_id=agent_id,
                data=data,
                hora=hora,
                duracao_minutos=30
            )
            if disponibilidade["disponivel"]:
                return [f"{data} {hora} disponível para agendamento."]
            else:
                # Sugerir próximos horários disponíveis
                sugestoes = []
                for dias in range(1, 11):
                    data_alvo = agora + timedelta(days=dias)
                    if data_alvo.weekday() >= 5:
                        continue

                    blocos = [
                        (time(8, 0), time(12, 0)),
                        (time(13, 30), time(18, 0)),
                    ]

                    for inicio, fim in blocos:
                        horario_atual = datetime.combine(data_alvo.date(), inicio)
                        while horario_atual.time() < fim:
                            hora_alt = horario_atual.strftime("%H:%M")
                            data_alt = horario_atual.strftime("%Y-%m-%d")

                            disponibilidade_alt = await check_availability(
                                session=session,
                                agent_id=agent_id,
                                data=data_alt,
                                hora=hora_alt,
                                duracao_minutos=30
                            )

                            if disponibilidade_alt["disponivel"]:
                                sugestoes.append(f"{data_alt} {hora_alt}")
                            if len(sugestoes) >= 5:
                                break
                            horario_atual += timedelta(minutes=30)

                    if len(sugestoes) >= 5:
                        break

                return [f"Horário {data} {hora} indisponível. Sugestões:"] + sugestoes

        # Caso não tenha data/hora: listar todos os disponíveis nos próximos 10 dias
        for dias in range(1, 11):
            data_alvo = agora + timedelta(days=dias)
            if data_alvo.weekday() >= 5:
                continue

            blocos = [
                (time(8, 0), time(12, 0)),
                (time(13, 30), time(18, 0)),
            ]

            for inicio, fim in blocos:
                horario_atual = datetime.combine(data_alvo.date(), inicio)
                while horario_atual.time() < fim:
                    hora_formatada = horario_atual.strftime("%H:%M")
                    data_formatada = horario_atual.strftime("%Y-%m-%d")

                    disponibilidade = await check_availability(
                        session=session,
                        agent_id=agent_id,
                        data=data_formatada,
                        hora=hora_formatada,
                        duracao_minutos=30
                    )

                    if disponibilidade["disponivel"]:
                        horarios_disponiveis.append(f"{data_formatada} {hora_formatada}")

                    horario_atual += timedelta(minutes=30)

        return horarios_disponiveis or ["Nenhum horário disponível nos próximos 10 dias."]
    
@tool
async def serv_agenda(data: str, hora: str, cliente: str, assunto: str, email_cliente: str) -> dict:
    """
    Agenda um horário no Google Calendar.
    A IA deve garantir que todos os campos sejam fornecidos: data, hora, nome do cliente, assunto e e-mail do cliente.
    Sempre consulte a disponibilidade antes de agendar.
    O email deve ser captado do Estado Atual e caso não esteja lá solicite ao usuário. NUNCA INVENTE EMAIL!

    Args:
        data (str): Data no formato YYYY-MM-DD
        hora (str): Hora no formato HH:MM (24h)
        cliente (str): Nome do cliente
        assunto (str): Assunto do compromisso
        email_cliente (str): E-mail do cliente para ser adicionado como convidado

    Returns:
        Mensagem de confirmação do agendamento.
    """
    campos_faltando = []

    if not data:
        campos_faltando.append("data")
    if not hora:
        campos_faltando.append("hora")
    if not cliente:
        campos_faltando.append("cliente")
    if not assunto:
        campos_faltando.append("assunto")
    if not email_cliente:
        campos_faltando.append("email_cliente")

    if campos_faltando:
        campos = ", ".join(campos_faltando)
        return {
            "erro": f"Parâmetro(s) faltando: {campos}. Me informe ou solicite ao usuário caso não tenha."
        }

    agent_id = 1
    duracao_minutos = 60  # duração padrão de 1 hora

    async with async_session() as session:
        # Verifica se o horário está disponível
        disponibilidade = await check_availability(
            session=session,
            agent_id=agent_id,
            data=data,
            hora=hora,
            duracao_minutos=duracao_minutos
        )

        if not disponibilidade["disponivel"]:
            return {
                "erro": "Horário indisponível. Consulte os horários disponíveis antes de tentar agendar."
            }

        try:
            resultado = await schedule_event(
                session=session,
                agent_id=agent_id,
                data=data,
                hora=hora,
                cliente=cliente,
                assunto=assunto,
                duracao_minutos=duracao_minutos,
                email_convidado=email_cliente  # novo argumento
            )
            return resultado
        except Exception as e:
            return {"erro": f"Erro ao agendar: {str(e)}"}