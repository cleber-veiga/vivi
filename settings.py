# app/config.py
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configurações da aplicação."""
    PROJECT_NAME: str = "Vivi"
    DESCRIPTION: str = "Serviço de Inteligência Para WhatsApp da Vivi"
    VERSION: str = "1.0.0"
    URL_APPLICATION: str = "https://seusite.com"

    # Configurações de CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]
    
    # Banco de dados (Neon PostgreSQL)
    POSTGRES_URL: str = Field(..., env="POSTGRES_URL")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_TEMPERATURE: Optional[float] = Field(default=0.5, env="OPENAI_TEMPERATURE")
    OPENAI_MAX_TOKENS: Optional[int] = Field(default=4096, env="OPENAI_MAX_TOKENS")

    #NGrok
    SERVER_PORT: int = Field(8000, env="SERVER_PORT")
    NGROK_AUTH_TOKEN: str = Field(..., env="NGROK_AUTH_TOKEN")
    USE_NGROK: bool = Field(False, env="USE_NGROK")

    #Twilio
    TWILIO_AUTH_TOKEN: str = Field(..., env="TWILIO_AUTH_TOKEN")
    AGENT_ENDPOINT: str = Field(..., env="AGENT_ENDPOINT")
    TWILIO_ACCOUNT_SID: str = Field(..., env="TWILIO_ACCOUNT_SID")
    
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
