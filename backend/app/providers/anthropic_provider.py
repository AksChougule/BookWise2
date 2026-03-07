from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any

import httpx
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.providers.base_provider import BaseProvider, ProviderError, ProviderResult

logger = logging.getLogger(__name__)


def _log_retry_attempt(state: RetryCallState) -> None:
    exception = state.outcome.exception() if state.outcome else None
    logger.warning(
        "anthropic_retrying",
        extra={
            "event": "anthropic_retrying",
            "attempt_number": state.attempt_number,
            "next_sleep_s": state.next_action.sleep if state.next_action else None,
            "error": str(exception) if exception else None,
            "route": "/v1/messages",
        },
    )


class AnthropicProvider(BaseProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.anthropic_api_key
        self.model = settings.anthropic_model
        self.base_url = "https://api.anthropic.com/v1"

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )
    async def _call_messages(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not configured")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        start = perf_counter()
        logger.info(
            "anthropic_request_started",
            extra={
                "event": "anthropic_request_started",
                "route": "/v1/messages",
                "model": payload.get("model"),
            },
        )

        async with httpx.AsyncClient(timeout=130.0) as client:
            try:
                response = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)
            except (httpx.TimeoutException, httpx.ConnectError):
                duration_ms = int((perf_counter() - start) * 1000)
                logger.exception(
                    "anthropic_request_failed",
                    extra={
                        "event": "anthropic_request_failed",
                        "route": "/v1/messages",
                        "duration_ms": duration_ms,
                        "model": payload.get("model"),
                        "error_type": "provider_timeout",
                    },
                )
                raise

        duration_ms = int((perf_counter() - start) * 1000)
        logger.info(
            "anthropic_request_completed",
            extra={
                "event": "anthropic_request_completed",
                "route": "/v1/messages",
                "duration_ms": duration_ms,
                "model": payload.get("model"),
                "status_code": response.status_code,
            },
        )

        if response.status_code >= 500:
            raise httpx.TimeoutException(f"Anthropic upstream server error: {response.status_code}")

        if response.status_code == 429:
            raise ProviderError(
                f"Anthropic API error ({response.status_code}): {response.text}",
                error_type="provider_rate_limited",
                error_context={"status_code": response.status_code},
            )

        if response.status_code >= 400:
            raise ProviderError(
                f"Anthropic API error ({response.status_code}): {response.text}",
                error_type="unknown",
                error_context={"status_code": response.status_code},
            )

        return response.json()

    @staticmethod
    def _extract_text(response_payload: dict[str, Any]) -> str:
        chunks: list[str] = []
        for item in response_payload.get("content", []):
            if not isinstance(item, dict):
                continue
            if item.get("type") != "text":
                continue
            text = item.get("text")
            if isinstance(text, str):
                chunks.append(text)

        content_text = "\n".join(chunks).strip()
        if not content_text:
            raise ProviderError(
                "Anthropic response did not include text content",
                error_type="schema_validation_failed",
            )
        return content_text

    async def generate_structured(
        self,
        *,
        prompt: str,
        schema_name: str,
        schema: dict,
        max_output_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        selected_model = model or self.model
        schema_json = json.dumps(schema, ensure_ascii=True)
        system_prompt = (
            "Return only valid JSON that matches the provided JSON schema exactly. "
            "Do not include markdown or extra text."
        )
        user_prompt = (
            f"Schema name: {schema_name}\n"
            f"JSON schema: {schema_json}\n\n"
            f"Task prompt:\n{prompt}"
        )

        payload = {
            "model": selected_model,
            "max_tokens": max_output_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        response_payload = await self._call_messages(payload)
        output_text = self._extract_text(response_payload)

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"Model returned invalid JSON: {exc}",
                error_type="schema_validation_failed",
                error_context={"json_error": str(exc)},
            ) from exc

        usage = response_payload.get("usage", {})
        prompt_tokens = usage.get("input_tokens")
        completion_tokens = usage.get("output_tokens")

        return ProviderResult(
            data=parsed,
            model=response_payload.get("model") or selected_model,
            tokens_prompt=prompt_tokens if isinstance(prompt_tokens, int) else None,
            tokens_completion=completion_tokens if isinstance(completion_tokens, int) else None,
        )
