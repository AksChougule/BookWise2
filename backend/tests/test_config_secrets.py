from app.config import get_settings


def test_file_secret_overrides_env(monkeypatch, tmp_path) -> None:
    openai_file = tmp_path / "openai_key"
    youtube_file = tmp_path / "youtube_key"
    openai_file.write_text("file-openai-key\n", encoding="utf-8")
    youtube_file.write_text(" file-youtube-key ", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    monkeypatch.setenv("YOUTUBE_API_KEY", "env-youtube-key")
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(openai_file))
    monkeypatch.setenv("YOUTUBE_API_KEY_FILE", str(youtube_file))
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.openai_api_key == "file-openai-key"
        assert settings.youtube_api_key == "file-youtube-key"
    finally:
        get_settings.cache_clear()


def test_database_url_prefers_database_url_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:////app/data/bookwise.db")
    monkeypatch.setenv("BOOKWISE_DB_URL", "sqlite:///./legacy.db")
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.database_url == "sqlite:////app/data/bookwise.db"
        assert settings.bookwise_db_url == "sqlite:////app/data/bookwise.db"
    finally:
        get_settings.cache_clear()
