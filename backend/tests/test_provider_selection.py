from app.config import get_settings
from app.providers import AnthropicProvider, OpenAIProvider, get_provider, reset_provider_factory


def test_default_provider_is_openai(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    get_settings.cache_clear()
    reset_provider_factory()

    provider = get_provider()
    assert isinstance(provider, OpenAIProvider)


def test_can_select_anthropic_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    get_settings.cache_clear()
    reset_provider_factory()

    provider = get_provider()
    assert isinstance(provider, AnthropicProvider)

    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    get_settings.cache_clear()
    reset_provider_factory()
