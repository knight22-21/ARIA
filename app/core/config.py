"""Application configuration, loaded from environment / .env."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    aria_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # LLM
    llm_provider: Literal["groq", "ollama"] = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    embed_model: str = "nomic-embed-text"

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Datastores
    database_url: str = "postgresql+asyncpg://aria:aria@localhost:5432/aria"
    redis_url: str = "redis://localhost:6379/0"

    # Security
    pii_encryption_key: str = ""
    dashboard_jwt_secret: str = "change-me-in-production"

    @property
    def is_dev(self) -> bool:
        return self.aria_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
