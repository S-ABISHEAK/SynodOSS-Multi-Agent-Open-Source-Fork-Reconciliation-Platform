import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://synodoss:synodoss_pass@localhost:5432/synodoss")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Phase 2 Agent Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    MAX_ROUNDS: int = 4
    MAX_TOKENS_PER_AGENT: int = 2048
    MAX_EVIDENCE_ITEMS: int = 5
    
    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
