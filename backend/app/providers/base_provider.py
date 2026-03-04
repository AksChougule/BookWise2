from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    pass


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
    ) -> ProviderResult:
        raise NotImplementedError
