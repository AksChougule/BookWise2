from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BookWise 2"
    api_prefix: str = "/api"
    bookwise_db_url: str = "sqlite:///./bookwise.db"

    openlibrary_base_url: str = "https://openlibrary.org"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.2"

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    curated_books_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "curated_books.yml"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
