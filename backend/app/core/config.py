"""
ContextPulse Configuration & LLM Pricing Economics Settings.
"""

from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ContextPulse"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database Settings
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgrespassword@localhost:5432/contextpulse"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # LLM Context Caching Rules
    MIN_CACHE_PREFIX_TOKENS: int = 1024  # Industry minimum threshold for prompt caching
    DEFAULT_CACHE_TTL_SECONDS: int = 300  # 5 minutes TTL for active KV cache blocks

    # Model Pricing Tiers ($ per 1M tokens)
    # [base_input, cache_write_input, cache_read_input, output]
    PRICING_TABLE: Dict[str, Dict[str, float]] = {
        "claude-3-5-sonnet": {
            "base_input": 3.00,
            "cache_write": 3.75,
            "cache_read": 0.30,  # 90% discount on cache hit
            "output": 15.00,
        },
        "gpt-4o": {
            "base_input": 2.50,
            "cache_write": 2.50,
            "cache_read": 1.25,  # 50% discount on cache hit
            "output": 10.00,
        },
        "claude-3-haiku": {
            "base_input": 0.25,
            "cache_write": 0.30,
            "cache_read": 0.03,  # 90% discount on cache hit
            "output": 1.25,
        },
    }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
