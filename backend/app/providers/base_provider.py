from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_type: str = "unknown",
        error_context: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.error_context = error_context or {}


@dataclass(slots=True)
class ProviderResult:
    data: dict
    model: str
    tokens_prompt: int | None
    tokens_completion: int | None


class BaseProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self,
        *,
        prompt: str,
        schema_name: str,
        schema: dict,
        max_output_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        raise NotImplementedError
