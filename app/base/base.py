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
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from app.base.prompt import (
    AGENT_PREFIX_REACT,
    AGENT_SUFFIX_REACT,
    PROMPT
)
from langgraph.errors import GraphRecursionError
from sqlalchemy.ext.asyncio import AsyncSession

class UniqueToolNode(ToolNode):
    async def invoke(self, state):
        tool_calls = [m.tool_calls for m in state["messages"] if hasattr(m, "tool_calls")][-1]
        used_tools = state.get("tools_used", set())
        updated_messages = []

        for call in tool_calls:
            tool_name = call["name"]
            if tool_name in used_tools:
                updated_messages.append(
                    ToolMessage(name=tool_name, content="Essa ferramenta já foi utilizada.")
                )
                continue
            tool = self.tools_by_name.get(tool_name)
            if tool:
                output = await tool.ainvoke(call["args"])
                updated_messages.append(
                    ToolMessage(name=tool_name, content=str(output))
                )
                used_tools.add(tool_name)

        state["tools_used"] = used_tools
        state["messages"].extend(updated_messages)
        return state

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

    def _build_parameters_from_state(self, state: dict) -> str:
        keys_permitidas = ["phone", "name", "email", "address", "cnpj", "corporate_reason"]

        parameters = []
        for key in keys_permitidas:
            if state.get(key) is not None:
                parameters.append(f"<{key}>{state.get(key)}</{key}>")
            else:
                parameters.append(f"<{key}>Ainda não informado</{key}>")
        return "".join(parameters)

    def _build_workflow(self, agent_runnable, tools):
        workflow = StateGraph(AgentState)

        workflow.add_node("agent", agent_runnable)
        # workflow.add_node("tools", ToolNode(tools))
        workflow.add_node("tools", UniqueToolNode(tools))
        workflow.set_entry_point("agent")

        def route(state: AgentState) -> str:
            last_msg = state["messages"][-1]

            if isinstance(last_msg, AIMessage):
                content = last_msg.content

                # Se houver resposta final explícita, encerrar
                if "Resposta Final:" in content:
                    return END

                # Se houver tool_call nativa, executar
                if last_msg.tool_calls:
                    return "tools"

                # Se houver instruções de ação mas sem resposta final explícita
                padrao_acao = re.search(r"Ação:\s*(\w+)", content)
                padrao_entrada = re.search(r"Entrada de Ação:\s*(```python)?\{.*?\}(```)?", content, re.DOTALL)

                if padrao_acao and padrao_entrada:
                    return "tools"

            return END

        workflow.add_conditional_edges("agent", route)
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=MemorySaver())
    
    def _extract_final_block(self, messages):
        """
        Retorna as mensagens a partir do último HumanMessage (inclusive) até o final.
        """
        index_ultima_human = -1
        for i in reversed(range(len(messages))):
            if isinstance(messages[i], HumanMessage):
                index_ultima_human = i
                break
        
        if index_ultima_human == -1:
            return messages
        
        return messages[index_ultima_human:]
    
    def _build_memory_recent(self, message_json):
        converted_messages = []
        for msg in message_json:
            if msg["role"] == "user":
                converted_messages.append(f"<user>{msg["content"]}</user>")
            elif msg["role"] == "assistant":
                converted_messages.append(f"<vivi>{msg["content"]}</vivi>")
        return "".join(converted_messages)
    
    def _build_contextual_prompt(self, mensagens):
        linhas = []
        for msg in mensagens:
            if isinstance(msg, ToolMessage):
                if not msg.name.startswith("capture"):
                    linhas.append(f"<{msg.name}>{msg.content}</{msg.name}>")
        return "".join(linhas)

    async def invoke(self, question):
        llm = self.llm_factory.get_llm()
        llm_formulator = self.llm_factory.get_formulation_llm()

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
        memory_recent_str = self._build_memory_recent(memory_recent)
        memory_recent = simple_memory.message_converter(memory_recent)

        initial_state = {
            "messages": memory_recent + [HumanMessage(content=question)],
            "agent_scratchpad": [],
            "phone": self.phone,
            "tools_used": set()
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
            AGENT_PREFIX_REACT,
            AGENT_SUFFIX_REACT
        ])
        tools_used_str = ", ".join(initial_state["tools_used"]) or "nenhuma até o momento"
        system_prompt = template \
            .replace("{tool_names}", tool_names) \
            .replace("{now}", str(now)) \
            .replace("{phone}", str(self.phone)) \
            .replace("{memory}", str(memory_recent_str)) \
            .replace("{tools_descriptions}", str(tools_descriptions)) \
            .replace("{current_state}", str(current_state)) \
            .replace("{tools_used_str}", tools_used_str)

        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("messages"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

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

        config = {"configurable": {
            "thread_id": f"session_{str(uuid.uuid4())}",
            "recursion_limit": 10
            }
        }

        try:
            result_state = await app.ainvoke(initial_state, config=config, interrupt_after=["10"])
        except GraphRecursionError as e:
            result_state = initial_state
        
        final_block = self._extract_final_block(result_state["messages"])
        tool_content = self._build_contextual_prompt(final_block)

        template_formulate = PromptTemplate.from_template(PROMPT)

        chain = template_formulate | llm_formulator

        response = await chain.ainvoke({
            "now": str(now),
            "tool_content": tool_content,
            "summary": summary,
            "memory": memory_recent_str,
            "parameters": self._build_parameters_from_state(result_state),
            "input": question
        })
        response = response.content

        if not response or not str(response).strip():
            response = self.extract_resposta_final_from_state(result_state)

        return {
            "resposta": response,
            "metadata": self._build_metadata_from_state(result_state)
        }