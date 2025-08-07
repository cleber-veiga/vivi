from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.callbacks.base import BaseCallbackManager
from settings import settings  # Agora importamos diretamente as configurações


class LLMFactory:
    """
    Fábrica de LLMs (OpenAI) baseada diretamente em variáveis de ambiente via `settings`.
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE or 0.5
        self.max_tokens = settings.OPENAI_MAX_TOKENS or 4096

    def validate_credentials(self) -> dict:
        """Valida se os dados estão completos."""
        if not self.api_key or not self.model:
            return {
                'error': True,
                'message': 'OPENAI_API_KEY ou OPENAI_MODEL não definidos no settings.'
            }

        return {
            'error': False,
            'message': '',
            'llm_credentials': {
                'api_key': self.api_key,
                'model': self.model,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            }
        }

    def get_llm(self, callback_manager: Optional[BaseCallbackManager] = None):
        """
        Retorna a instância principal da LLM (OpenAI).
        """
        return ChatOpenAI(
            openai_api_key=self.api_key,
            model="o4-mini",
            temperature=1,
            max_tokens=4096,
            callback_manager=callback_manager
        )
    
    def get_formulation_llm(self, callback_manager: Optional[BaseCallbackManager] = None):
        """
        Retorna a instância principal da LLM (OpenAI).
        """
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=512,
            callback_manager=callback_manager
        )