from __future__ import annotations

from app.providers.base_provider import BaseProvider, ProviderError, ProviderResult


class FakeLLMProvider(BaseProvider):
    call_count = 0

    def __init__(self, model: str = "fake-llm") -> None:
        self.model = model
        self.number_of_calls = 0

    @classmethod
    def reset_call_count(cls) -> None:
        cls.call_count = 0

    async def generate_key_ideas(self, *, prompt: str, max_output_tokens: int) -> ProviderResult:
        _ = (prompt, max_output_tokens)
        return ProviderResult(
            data={
                "key_ideas": "- Deterministic idea 1\n- Deterministic idea 2\n- Deterministic idea 3",
            },
            model=self.model,
            tokens_prompt=42,
            tokens_completion=84,
        )

    async def generate_critique(self, *, prompt: str, max_output_tokens: int) -> ProviderResult:
        _ = (prompt, max_output_tokens)
        return ProviderResult(
            data={
                "strengths": "- Clear structure\n- Concrete examples",
                "weaknesses": "- Limited opposing views\n- Some repetition",
                "who_should_read": "Readers who want a practical overview and actionable takeaways.",
            },
            model=self.model,
            tokens_prompt=36,
            tokens_completion=72,
        )

    async def generate_structured(
        self,
        *,
        prompt: str,
        schema_name: str,
        schema: dict,
        max_output_tokens: int,
    ) -> ProviderResult:
        _ = schema
        FakeLLMProvider.call_count += 1
        self.number_of_calls += 1

        if schema_name == "key_ideas_response":
            return await self.generate_key_ideas(prompt=prompt, max_output_tokens=max_output_tokens)

        if schema_name == "critique_response":
            return await self.generate_critique(prompt=prompt, max_output_tokens=max_output_tokens)

        raise ProviderError(
            f"Unsupported schema_name for FakeLLMProvider: {schema_name}",
            error_type="schema_validation_failed",
            error_context={"schema_name": schema_name},
        )
