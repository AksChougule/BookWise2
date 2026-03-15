from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_secret_from_file(path: str | None) -> str | None:
    if not path:
        return None
    try:
        secret = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"Could not read secret file at {path}") from exc
    return secret or None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "BookWise 2"
    api_prefix: str = "/api"
    database_url: str = Field(
        default="sqlite:///./bookwise.db",
        validation_alias=AliasChoices("DATABASE_URL", "BOOKWISE_DB_URL"),
    )

    openlibrary_base_url: str = "https://openlibrary.org"
    youtube_base_url: str = "https://www.googleapis.com/youtube/v3"
    youtube_api_key: str | None = None
    youtube_api_key_file: str | None = None
    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: str | None = None
    openai_api_key_file: str | None = None
    openai_model: str = "gpt-5.2"
    summary_llm_model: str = "gpt-5.2"
    key_ideas_model: str = "gpt-5.2"
    critique_model: str = "gpt-5.2"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    generation_lease_seconds: int = 100

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    curated_books_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "curated_books.yml"
    )

    @property
    def bookwise_db_url(self) -> str:
        return self.database_url

    @model_validator(mode="after")
    def _resolve_file_based_secrets(self) -> "Settings":
        openai_from_file = _read_secret_from_file(self.openai_api_key_file)
        if openai_from_file is not None:
            self.openai_api_key = openai_from_file

        youtube_from_file = _read_secret_from_file(self.youtube_api_key_file)
        if youtube_from_file is not None:
            self.youtube_api_key = youtube_from_file

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
