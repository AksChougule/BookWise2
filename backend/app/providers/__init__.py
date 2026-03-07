from collections.abc import Callable

from app.providers.base_provider import BaseProvider
from app.providers.openai_provider import OpenAIProvider

ProviderFactory = Callable[[], BaseProvider]

_provider_factory: ProviderFactory = OpenAIProvider


def get_provider() -> BaseProvider:
    return _provider_factory()


def set_provider_factory(factory: ProviderFactory) -> None:
    global _provider_factory
    _provider_factory = factory


def reset_provider_factory() -> None:
    global _provider_factory
    _provider_factory = OpenAIProvider


__all__ = [
    "BaseProvider",
    "get_provider",
    "set_provider_factory",
    "reset_provider_factory",
]
