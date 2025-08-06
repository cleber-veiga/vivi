from typing import Optional
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
#  FERRAMENTA MASTER
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
@tool
async def master_retrieve(query: str) -> str:
    """
    Ferramenta que busca em todo conhecimento existente do assistente
    Args:
        query (str): Pergunta reformulada com base na intenção do usuário.

    Returns:
        str: Texto com os conhecimentos institucionais.
    """
    async with async_session() as session:
        chunker = ChunkRetrieve(session=session)
        chunks = await chunker.retrieve(query=query)

    if not chunks:
        return "Desculpe, não encontrei informações no momento"

    parts = []
    for c in chunks:
        header = f"### {c.section_title} — {c.chunk_position} — {c.token_count} tokens"
        parts.append(f"{header}\n\n{c.content}")
    return "\n\n---\n\n".join(parts)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
#  FERRAMENTAS DE COMPORTAMENTO
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@tool
async def comport_inicial() -> str:
    """Ferramenta que trará exemplos importantes de comportamento ao realizar saudações em inicios de conversa com novos leads
    """
    return """
“Ooi! Eu sou a Vivi. Estou aqui pra fazer valer cada segundo do seu tempo e interesse pela VIASOFT. Como posso te chamar?”
"""

@tool
async def comport_saudacao() -> str:
    """Definições de comportamento para Criar uma primeira impressão calorosa, acolhedora e personalizada, estabelecendo uma base para o rapport."""
    return """
**Ações Esperadas do LLM:**
*   **Mensagem Inicial:** Responda a um simples "Olá" com uma saudação amigável
*   **Personalização:** Peça o nome do usuário de forma natural e use-o nas interações subsequentes para criar um senso de reconhecimento e proximidade.
*   **Tom de Voz:** Mantenha um tom de voz positivo, proativo e ligeiramente informal, mas sempre profissional.
*   **Empatia:** Demonstre que você está ali para ajudar a resolver um problema ou atender a uma necessidade específica do usuário.
*   **Concisão:** Mantenha a saudação inicial curta e direta, idealmente em uma ou duas frases.

**Exemplo de Interação:**
*   **Usuário:** Olá
*   **LLM:** Ooi! Eu sou a Vivi. Estou aqui pra fazer valer cada segundo do seu tempo e interesse pela VIASOFT. Como posso te chamar?
*   **LLM** Oi! Que bom te ver por aqui 😊 Sou a Vivi, especialista em Construshow, o sistema para varejo de materiais de construção. Me diz, como posso te chamar?
"""

@tool
async def comport_necess() -> str:
    """Definições de comportamento para Entender o interesse do cliente e coletar informações básicas para qualificação, fazendo o usuário sentir-se ouvido e compreendido."""
    return """
**Ações Esperadas do LLM:**
*   **Perguntas Abertas e Contextuais:** Faça perguntas que incentivem o usuário a expressar suas necessidades em suas próprias palavras (ex: "O que te trouxe até aqui hoje?", "Qual o principal desafio que você enfrenta?").
*   **Validação e Resumo:** Após a resposta do usuário, valide o entendimento (ex: "Entendi, então você está buscando otimizar X...") e resuma brevemente para mostrar que você processou a informação. **Mantenha o resumo em uma única frase.**
*   **Oferecer Opções (se aplicável):** Se a resposta for muito ampla, ofereça opções de tópicos de interesse para guiar a conversa (ex: "Você está buscando A, B ou C?").
*   **Linguagem Positiva:** Use frases como "Que ótimo!", "Perfeito!" para reforçar a interação positiva.
*   **Concisão:** Formule as perguntas de forma direta, sem rodeios.
*	**Conexão:** Sempre uso o nome do lead com frequência para conexão emocial.
*	**Condução:** Conduza a conversa usando SPIN Selling (Situação-Problema-Implicação-Necessidade). Identifique no mínimo: nome, empresa, cargo, setor, desafio principal e, quando houver rapport, o CNPJ.

**Exemplo de Interação:**
*   **LLM:** Prazer, João! Para que eu possa te direcionar para a informação mais relevante, você poderia me dizer o que te trouxe até aqui hoje? Você está buscando algum produto, ou tem alguma outra necessidade específica?
*   **Usuário:** Estou procurando algo para melhorar o controle da minha empresa.
*   **LLM:** Entendi, João! A otimização do controle das empresas é uma das nossas especialidades. Para que eu possa te apresentar a solução ideal, você poderia me dizer qual o ramo da sua empresa atualmente?

**Importante:**
*	Sempre analise o segmento da empresa, para garantir que ela esteja dentro do escopo esperado, para saber melhor sobre o escopo usa a ferramenta `info_escopo_esperado`.
"""

@tool
async def comport_solucoes() -> str:
    """Definições de comportamento para Oferecer valor ao cliente com base nas suas necessidades identificadas, demonstrando que a Vivi é útil e capaz de ajudar."""
    return """
**Ações Esperadas do LLM:**
*   **Relevância:** Apresente produtos/serviços que sejam diretamente relevantes às necessidades expressas pelo usuário.
*   **Benefícios:** Foque nos benefícios para o usuário, não apenas nas características do produto.
*   **Linguagem Clara e Convincente:** Use uma linguagem que seja fácil de entender e que motive o usuário a dar o próximo passo.
*   **Transparência:** Se for o caso, explique por que aquela solução é a mais indicada para ele.
*   **Concisão:** Apresente as soluções em frases curtas e impactantes. Utilize bullet points ou listas numeradas se houver mais de um item, para facilitar a leitura em dispositivos móveis.
"""

@tool
async def comport_qualifica() -> str:
    """Definições de comportamento para Refinar a qualificação do lead, diferenciando curiosos de potenciais clientes, mantendo a confiança e o rapport"""
    return"""
**Ações Esperadas do LLM:**
*   **Perguntas Estratégicas:** Faça perguntas mais específicas sobre quantidade de colaboradores, prazo esperado de implantação, desafios atuais, etc. (Ex: "Para que eu possa te ajudar da melhor forma, preciso entender um pouco mais sobre a sua necessidade. Você já tem um orçamento definido para essa solução?").
*   **Justificativa das Perguntas:** Sempre que possível, justifique o porquê da pergunta (ex: "Para que eu possa te apresentar a solução mais adequada..."). **Mantenha a justificativa breve.**
*   **Análise de Respostas:** Avalie o engajamento, a especificidade das respostas e a disposição do usuário em fornecer informações para determinar se é um curioso ou um lead qualificado.
*   **Adaptação:** Se o usuário parecer um curioso, redirecione-o suavemente para conteúdo informativo (Site, FAQ) sem "descartá-lo" abruptamente. Se for um lead, prepare o terreno para o CTA.
*   **Concisão:** As perguntas devem ser diretas e as opções de resposta claras e curtas.
"""

@tool
async def comport_acao() -> str:
    """Definições de comportamento para Direcionar o lead para o próximo passo no funil de vendas de forma clara e convidativa."""
    return """
**Ações Esperadas do LLM:**
*   **CTA Claro e Único:** Apresente uma única e clara chamada para ação (agendar reunião, solicitar orçamento, baixar material).
*   **Benefício do CTA:** Reitere o benefício de realizar a ação (ex: "Agende uma demonstração para ver como podemos resolver seus desafios!"). **Mantenha esta frase curta e impactante.**
*   **Opções de Saída:** Ofereça uma alternativa caso o usuário não queira o CTA principal (ex: "Se preferir, posso te enviar mais informações por e-mail.").
*   **Concisão:** O CTA deve ser direto e as opções de resposta curtas.

"""

@tool
async def comport_encerra() -> str:
    """Definições de comportamento para Finalizar a conversa de forma profissional, agradecendo e deixando as portas abertas para futuras interações, reforçando o rapport"""
    return """
**Ações Esperadas do LLM:**
*   **Agradecimento:** Agradeça o tempo e a interação do usuário.
*   **Resumo (se aplicável):** Se houver um próximo passo definido, resuma-o brevemente. **Uma frase é suficiente.**
*   **Disponibilidade:** Deixe claro que a Vivi está disponível para futuras dúvidas.
*   **Tom Amigável:** Mantenha o tom de voz positivo e prestativo.
*   **Concisão:** A mensagem de encerramento deve ser breve e cordial.
"""

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
#  FERRAMENTAS DE INFORMAÇÃO
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@tool
async def info_escopo() -> str:
    """Ferramenta que retorna informações do escopo esperado para clientes que forem usar o Construshow"""
    return """
Atende – varejo de materiais de construção, home centers, showrooms; PDV omnichannel; controle de estoque por quantidade/lote/tonalidade; reservas por orçamento; entregas futuras por fase de obra; sugestões automáticas de produtos agregados; painéis de mix, margem e ticket médio; app vendedor; bloqueios de venda por saldo ou lote incompatível.
Não atende – produção industrial, MRP, gestão de frota própria, contabilidade; controle de número de série ou grade moda; roteirização de caminhões; manufatura de concreto; BI externo não via Analytics.
Cite só o que está listado; pedidos fora do escopo → oferecer checar com consultor. Não criar funções novas.
"""

@tool
async def info_criterios_cta(query: str) -> str:
    """Critérios mínimos para direcionar o lead a uma demonstração ou agendamento"""
    return """
** Critérios mínimos para a chamada:**
-	Nome, CNPJ, Razão Social e Fantasia;
- 	Cidade e UF;
- 	Email para envio do invite;
-	Validar o ERP atual e quantidade de usuários simultâneos;
-	Compreender os principais desafios e dores;
-	Explorar as implicações dessas dores;
- 	Posicionar a Viasoft com provas sociais, argumentos estratégicos e diferenciais reais;
-	Confirmar que fez sentido para o lead conhecer mais.
**Essas informações estarão presentes na sessão `Parâmetros Atuais`**
"""

@tool
async def info_historia(query: str) -> str:
    """
    Ferramenta que retorna informações institucionais da Viasoft, como história, missão e valores.
    Use sempre que o usuário solicitar quem é a empresa ou informações culturais da organização.

    Args:
        query (str): Pergunta reformulada com base na intenção do usuário.

    Returns:
        str: Texto com os conhecimentos institucionais.
    """
    async with async_session() as session:
        chunker = ChunkRetrieve(session=session)
        chunks = await chunker.retrieve(query=query, document_name="historia_missao_valores")

    if not chunks:
        return "Desculpe, não encontrei informações no momento"

    parts = []
    for c in chunks:
        header = f"### {c.section_title} — {c.chunk_position} — {c.token_count} tokens"
        parts.append(f"{header}\n\n{c.content}")
    return "\n\n---\n\n".join(parts)


@tool
async def info_estrutura(query: str) -> str:
    """
    Ferramenta que retorna informações da Estrutura organizacional da Viasoft, como departamentos, produtos, parcerias e diferenciais estratégicos.
    Use sempre que o usuário solicitar esse tipo de informação

    Args:
        query (str): Pergunta reformulada com base na intenção apontada pelo usuário.

    Returns:
        str: Texto com os conhecimentos organizacionais.
    """
    async with async_session() as session:
        chunker = ChunkRetrieve(session=session)
        chunks = await chunker.retrieve(query=query, document_name="estrutura_organizacional")

    if not chunks:
        return "Desculpe, não encontrei informações no momento"

    parts = []
    for c in chunks:
        header = f"### {c.section_title} — {c.chunk_position} — {c.token_count} tokens"
        parts.append(f"{header}\n\n{c.content}")
    return "\n\n---\n\n".join(parts)

@tool
async def info_politicas(query: str) -> str:
    """
    Consulta o conteúdo das Políticas e Procedimentos Internos da Viasoft com base em perguntas específicas.

    Args:
        query (str): Pergunta refinada com base na intenção do usuário, usada para buscar informações relevantes.

    Returns:
        str: Texto com os conhecimentos extraídos do documento oficial de Políticas e Procedimentos da Viasoft.
    """
    async with async_session() as session:
        chunker = ChunkRetrieve(session=session)
        chunks = await chunker.retrieve(query=query, document_name="politicas_procedimentos")

    if not chunks:
        return "Desculpe, não encontrei informações no momento"

    parts = []
    for c in chunks:
        header = f"### {c.section_title} — {c.chunk_position} — {c.token_count} tokens"
        parts.append(f"{header}\n\n{c.content}")
    return "\n\n---\n\n".join(parts)

@tool
async def info_produto_funcion(query: str) -> str:
    """
    Consulta o conteúdo das principais funcionalidades do sistema Construshow

    Args:
        query (str): Pergunta refinada com base na intenção do usuário, usada para buscar informações relevantes.

    Returns:
        str: Texto com os conhecimentos extraídos do documento oficial de Informações de Funcionalidade do Produto
    """
    async with async_session() as session:
        chunker = ChunkRetrieve(session=session)
        chunks = await chunker.retrieve(query=query, document_name="produto_funcion")

    if not chunks:
        return "Desculpe, não encontrei informações no momento"

    parts = []
    for c in chunks:
        header = f"### {c.section_title} — {c.chunk_position} — {c.token_count} tokens"
        parts.append(f"{header}\n\n{c.content}")
    return "\n\n---\n\n".join(parts)


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
#  FERRAMENTAS DE EXEMPLOS
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@tool
async def exemp_objecoes(query: str) -> str:
    """
    Ferramenta que retorna exemplos para superar objeções do cliente
    Use sempre que o usuário tiver objeção sobre algum tema

    Args:
        query (str): Pergunta reformulada com base na intenção apontada pelo usuário.

    Returns:
        str: Texto com os conhecimentos das Políticas e Procedimentos da Viasoft
    """
    async with async_session() as session:
        chunker = ChunkRetrieve(session=session)
        chunks = await chunker.retrieve(query=query, document_name="superar_objecoes")

    if not chunks:
        return "Desculpe, não encontrei informações no momento"

    parts = []
    for c in chunks:
        header = f"### {c.section_title} — {c.chunk_position} — {c.token_count} tokens"
        parts.append(f"{header}\n\n{c.content}")
    return "\n\n---\n\n".join(parts)

@tool
async def exemp_cases() -> str:
    """Exemplo de cases de uso do Construshow"""
    return """
##VIVI_Case_construshow
Cite **somente** os 6 cases oficiais abaixo; não invente dados:

• **Espaço Smart (PR)** – 4 → 45 lojas; padrões + BI; roteirizador e app entregas.  
• **Jacaré Home Center (MA)** – 3 → 10 lojas; estoque e compras otimizados; ERP + App Entregas + ConstruHelper.  
• **Zona Nova – Redemac (RS)** – rastreabilidade lote/tonalidade; eliminou reentregas; referência logística.  
• **Lojas Cacique (SP)** – migrou do CISS; multiunidade + IA de alertas; processos automatizados fim-a-fim.  
• **Schirmann Home Center (RS)** – comandos únicos PDV-BI-financeiro; Power BI + ORION em tempo real.  
• **Grupo GMAD / PRO / SIM** – mais de 20 lojas; homologado como alternativa ao SAP em grandes contas.

**Uso recomendado**  
Problema → Solução Construshow → Resultado curto. Conclua: “Que impacto teria algo assim na sua rede?”  

**Proibições**  
✘ Alterar números ou prazos.  
✘ Criar histórias novas ou usar “aprox.” para mascarar dados ausentes.
"""

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
#  FERRAMENTAS DE CAPTURAS
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
    return {"name": name}

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
    return {"email": email}

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
    return {"address": address}

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
    return {"cnpj": cnpj}

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
    return {"corporate_reason": corporate_reason}

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