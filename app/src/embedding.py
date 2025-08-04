# app/services/embedding_processor.py

from typing import List
from langchain_openai import OpenAIEmbeddings
from settings import settings


class EmbeddingProcessor:
    """
    Classe responsável por processar embeddings para documentos,
    com suporte inicial à OpenAI.
    """

    def __init__(self):
        self.openai_embedder = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)

    def embed_openai(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para uma lista de textos usando o modelo da OpenAI.

        Args:
            texts (List[str]): Lista de textos a serem vetorizados.

        Returns:
            List[List[float]]: Lista de vetores embeddings.
        """
        if not texts:
            raise ValueError("Lista de textos está vazia para geração de embeddings.")

        return self.openai_embedder.embed_documents(texts)
