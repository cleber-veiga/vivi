# app/config.py
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    """Configurações da aplicação."""
    PROJECT_NAME: str = "Vivi"
    DESCRIPTION: str = "Serviço de Inteligência Para WhatsApp da Vivi"
    VERSION: str = "1.0.0"
    URL_APPLICATION: str = "https://vivi-i6si.onrender.com"
    SERVER_PORT: int = Field(8080, env="SERVER_PORT")

    # Configurações de CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:3000"]
    
    # Banco de dados (Neon PostgreSQL)
    POSTGRES_URL: str = Field(..., env="POSTGRES_URL")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_TEMPERATURE: Optional[float] = Field(default=0.5, env="OPENAI_TEMPERATURE")
    OPENAI_MAX_TOKENS: Optional[int] = Field(default=4096, env="OPENAI_MAX_TOKENS")

    #NGrok
    NGROK_AUTH_TOKEN: str = Field(..., env="NGROK_AUTH_TOKEN")
    USE_NGROK: bool = Field(False, env="USE_NGROK")

    #Twilio
    TWILIO_AUTH_TOKEN: str = Field(..., env="TWILIO_AUTH_TOKEN")
    TWILIO_ACCOUNT_SID: str = Field(..., env="TWILIO_ACCOUNT_SID")
    
    # Google Calendar
    GOOGLE_CLIENT_ID: str = Field(..., env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    GOOGLE_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    REDIRECT_URI: str = Field(..., env="REDIRECT_URI")

    GOOGLE_APPLICATION_CREDENTIALS: str = Field(..., env="GOOGLE_APPLICATION_CREDENTIALS")

    #Eleven Labs
    ELEVEN_LABS_API_KEY: str = Field(..., env="REDIRECT_URI")
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
