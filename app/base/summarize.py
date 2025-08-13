from app.core.factory import LLMFactory
from app.services.memory import MemoryService
from app.src.summarize import summarize_conversation_temp
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

PROMPT = """
Você é um assistente de conversas pelo WhatsApp especializado em reengajar leads que não responderam há algum tempo.
Sua missão é retomar o contato de forma leve, simpática e profissional.

Abaixo está um resumo da conversa até agora:
{summary}

Com base nesse contexto, crie UMA única mensagem curta e personalizada que:
- Reforce de forma sutil o tema ou objetivo da última interação.
- Incentive o lead a responder, despertando curiosidade ou interesse.
- Mantenha tom amigável, próximo e humano — evitando formalidade excessiva ou frases genéricas de robô.
- Não repita exatamente as frases já usadas anteriormente.
- Tenha no máximo 2 frases, sendo direta e envolvente.

Responda apenas com o texto final da mensagem, sem explicações ou formatações adicionais.
"""

async def generate_response_with_summary(session, phone) -> str:
    llm = LLMFactory().get_llm()

    # Busca memória; trata ausência
    lead = await MemoryService.get_memory_by_phone(session, phone)
    memory = getattr(lead, "conversation_mem", None) if lead else None

    # Gera resumo com fallback
    try:
        summary = await summarize_conversation_temp(memory or "", llm)
    except Exception:
        summary = ""

    # Se não houver contexto, manda um toque neutro
    if not summary or not summary.strip():
        return "Posso te ajudar a retomar de onde paramos? Se preferir, me diga um bom horário e eu sigo daqui. 🙂"

    prompt = PromptTemplate.from_template(PROMPT)
    chain = prompt | llm | StrOutputParser()

    try:
        text = await chain.ainvoke({"summary": summary})
    except Exception:
        # Fallback em caso de erro do LLM
        text = "Quer continuar de onde paramos? Me diga um horário que seja bom pra você. 🙂"

    # Normalização final
    return (text or "").strip()
