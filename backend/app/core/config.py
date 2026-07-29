"""Core application configuration for AuraSaaS."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings with local demo defaults."""

    app_name: str = "AuraSaaS"
    app_description: str = "Open-source AI Business Intelligence Agent Platform"
    api_prefix: str = "/api"

    deepseek_api_key: str = "sk-placeholder"
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_api_base: str = "https://api.deepseek.com"

    database_url: str = "sqlite:///./aura.db"
    redis_url: str = ""  # e.g. "redis://localhost:6379/0" — empty disables Redis (falls back to in-memory)
    chroma_dir: str = "./data/chroma"
    code_embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    code_embedding_cache_dir: str = "./data/huggingface"
    jwt_secret: str = "change-me-in-production"
    environment: str = "local"
    seed_demo_on_startup: bool = True
    force_reseed_demo: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    text_encoding: str = "utf-8"

    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2

    # MCP: JSON list of server configs, e.g. [{"name":"filesystem","command":["npx","-y","..."]}]
    mcp_servers: str = ""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
