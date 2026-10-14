"""Application settings and project paths."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Environment-backed application configuration."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Customer Churn Prediction and RAG API"
    app_version: str = "1.0.0"
    llm_provider: Literal["openai", "groq", "ollama"] = "ollama"
    openai_api_key: str | None = Field(default=None, repr=False)
    groq_api_key: str | None = Field(default=None, repr=False)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    database_url: str = (
        "postgresql+psycopg://churn_user:churn_password@localhost:5432/churn_db"
    )
    cors_origins: list[str] = ["http://localhost:5173"]
    model_path: Path = BACKEND_DIR / "data" / "processed" / "model.pkl"
    chroma_path: Path = BACKEND_DIR / "chroma_db"
    chroma_collection_path: Path = (
        BACKEND_DIR / "data" / "processed" / "chroma_collection.txt"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()