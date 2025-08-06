import re
from typing import Dict, List, Tuple
import uuid
from app.base.schemas import AgentState, MessagePayload
from app.core.factory import LLMFactory
from langgraph.prebuilt import ToolNode, create_react_agent
from app.core.memory import SimpleMemory
from app.services.memory import MemoryService
from app.src.summarize import summarize_conversation
from app.tools.index import tools
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.base.prompt import (
    AGENT_PREFIX,
    AGENT_INSTRUCTIONS,
    AGENT_SUFFIX
)
from sqlalchemy.ext.asyncio import AsyncSession


class BaseMessage:
    """
    Classe responsável por encapsular o processamento de uma mensagem recebida via API.
    """

    def __init__(self, request: MessagePayload, session: AsyncSession):
        self.request = request
        self.llm_factory = LLMFactory()
        self.session = session
        self.phone = self.request.phone.replace('whatsapp:+', '')
        

    async def handle(self):
        question = self.request.message
        phone = self.phone.replace('whatsapp:+', '')

        # 1. Buscar memória existente
        lead = await MemoryService.get_memory_by_phone(self.session, phone)
        if lead and lead.conversation_mem:
            memory = SimpleMemory(memory_data=lead.conversation_mem)
        else:
            memory = SimpleMemory()

        # 2. Adicionar a nova mensagem do usuário
        memory.add_message(role="user", content=question)

        # 3. Invocar o agente
        resultado = await self.invoke(question=question)

        resposta = resultado["resposta"]
        metadata = resultado["metadata"]

        # 4. Adicionar resposta do agente à memória
        memory.add_message(role="assistant", content=resposta)



        # 5. Salvar memória atualizada no banco
        await MemoryService.upsert_memory(
            self.session,
            phone=phone,
            memory=memory.to_dict(),
            metadata_json=metadata
        )

        return resposta

    def extract_resposta_final_from_state(self, state) -> str:
        """
        Extrai o conteúdo após 'Resposta Final:' da última AIMessage válida no estado do agente.

        Args:
            state (dict): Estado retornado pela execução do LangGraph.

        Returns:
            str: A resposta final extraída, ou uma mensagem padrão caso não exista.
        """
        messages = state.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                if "Resposta Final:" in msg.content:
                    match = re.search(r"Resposta Final:\s*(.*)", msg.content, re.DOTALL)
                    return match.group(1).strip() if match else msg.content
                elif not msg.tool_calls:
                    # Fallback: se não houver tool_call e parecer uma resposta final
                    return msg.content.strip()
            if "Ação:" in msg.content and "Resposta Final:" in msg.content:
                print("⚠️ Atenção: Ferramenta foi ignorada no fluxo. Ação declarada, mas não executada.")
        return "Desculpe, algo deu errado e acabei não entendendo sua pergunta. Por favor, não exite em perguntar novamente"

    def divide_memory(self, memoria: Dict[str, List[Dict[str, str]]], limite: int = 4) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Divide a memória da conversa entre as últimas N interações e o restante anterior.
        
        Args:
            memoria (dict): Dicionário no formato {"messages": [...]}
            limite (int): Quantidade de mensagens recentes a manter (padrão 4)

        Returns:
            Tuple[List, List]: (recentes, anteriores)
        """
        mensagens = memoria.get("messages", [])
        total = len(mensagens)

        if total <= limite:
            return mensagens, []  # tudo recente, nada anterior
        else:
            return mensagens[-limite:], mensagens[:-limite]
    def _build_metadata_from_state(self, state: dict) -> dict:
        """
        Extrai os campos úteis do estado do agente para salvar como metadata_json.
        """
        keys_permitidas = ["phone", "name", "email", "address", "cnpj", "corporate_reason"]
        return {key: state.get(key) for key in keys_permitidas if state.get(key) is not None}

    def _build_workflow(self, agent_runnable, tools):
        workflow = StateGraph(AgentState)

        workflow.add_node("agent", agent_runnable)
        workflow.add_node("tools", ToolNode(tools))
        workflow.set_entry_point("agent")

        def route(state: AgentState) -> str:
            last_msg = state["messages"][-1]
            
            # Verifica se há tool_calls (caso o modelo use isso nativamente)
            if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
                return "tools"
            
            # Verifica se há instruções de Ação explícitas no padrão ReAct
            content = last_msg.content if isinstance(last_msg, AIMessage) else ""
            
            padrao_acao = re.search(r"Ação:\s*(\w+)", content)
            padrao_entrada = re.search(r"Entrada de Ação:\s*(```python)?\{.*?\}(```)?", content, re.DOTALL)
            
            if padrao_acao and padrao_entrada:
                return "tools"

            # Caso contrário, encerra
            return END

        workflow.add_conditional_edges("agent", route)
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=MemorySaver())
    
    async def invoke(self, question):
        llm = self.llm_factory.get_llm()
        tools_agent = tools
        now = datetime.now()

        tool_names = ", ".join(t.name for t in tools_agent)
        tools_descriptions = "\n".join([f"{t.name}: {t.description}" for t in tools_agent])

        lead = await MemoryService.get_memory_by_phone(self.session, self.phone)
        if lead and lead.conversation_mem:
            memory = lead.conversation_mem
            memory_recent, memory_long = self.divide_memory(memory, limite=4)
        else:
            memory_recent, memory_long = [], []

        simple_memory = SimpleMemory()
        memory_recent = simple_memory.message_converter(memory_recent)

        initial_state = {
            "messages": memory_recent + [HumanMessage(content=question)],
            "agent_scratchpad": [],
            "phone": self.phone
        }

        if lead and lead.metadata_json:
            for key, value in lead.metadata_json.items():
                if key == "phone":
                    continue
                initial_state[key] = value
        
        metadata_dict = self._build_metadata_from_state(initial_state)
        current_state = "\n".join([f"- {k}: {v}" for k, v in metadata_dict.items()])
        
        summary = ""
        if memory_long:
            summary = await summarize_conversation(memory_long, llm)
            
        template = "\n\n".join([
            AGENT_PREFIX,
            AGENT_INSTRUCTIONS,
            AGENT_SUFFIX
        ])
        system_prompt = template.replace("{tool_names}", tool_names) \
            .replace("{now}", str(now)) \
            .replace("{phone}", str(self.phone)) \
            .replace("{summary}", str(summary)) \
            .replace("{tools_descriptions}", str(tools_descriptions)) \
            .replace("{current_state}", str(current_state))

        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("messages"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        print("======= SYSTEM PROMPT FINAL =======")
        print(system_prompt)
        print("===================================")

        react_runnable = create_react_agent(
            model=llm,
            tools=tools_agent,
            prompt=chat_prompt,
            state_schema=AgentState,
            debug=True,
            name="AgentVivi",
            version="v2",
            checkpointer=MemorySaver(),
        )

        app = self._build_workflow(agent_runnable=react_runnable, tools=tools)

        

        config = {"configurable": {"thread_id": f"session_{str(uuid.uuid4())}"}}

        result_state = await app.ainvoke(initial_state, config=config)

        return {
            "resposta": str(self.extract_resposta_final_from_state(result_state)),
            "metadata": self._build_metadata_from_state(result_state)
        }