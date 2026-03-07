from collections.abc import Callable

from app.config import get_settings
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base_provider import BaseProvider
from app.providers.openai_provider import OpenAIProvider

ProviderFactory = Callable[[], BaseProvider]

_provider_factory: ProviderFactory | None = None


def _default_factory() -> ProviderFactory:
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        return AnthropicProvider
    return OpenAIProvider


def get_provider() -> BaseProvider:
    factory = _provider_factory or _default_factory()
    return factory()


def set_provider_factory(factory: ProviderFactory) -> None:
    global _provider_factory
    _provider_factory = factory


def reset_provider_factory() -> None:
    global _provider_factory
    _provider_factory = None


__all__ = [
    "BaseProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "get_provider",
    "set_provider_factory",
    "reset_provider_factory",
]
