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
        "openai_retrying",
        extra={
            "event": "openai_retrying",
            "attempt_number": state.attempt_number,
            "next_sleep_s": state.next_action.sleep if state.next_action else None,
            "error": str(exception) if exception else None,
            "route": "/v1/responses",
        },
    )


class OpenAIProvider(BaseProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.base_url = "https://api.openai.com/v1"

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=_log_retry_attempt,
        reraise=True,
    )
    async def _call_responses(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start = perf_counter()
        logger.info(
            "openai_request_started",
            extra={
                "event": "openai_request_started",
                "route": "/v1/responses",
                "model": payload.get("model"),
            },
        )
        async with httpx.AsyncClient(timeout=130.0) as client:
            try:
                response = await client.post(f"{self.base_url}/responses", headers=headers, json=payload)
            except (httpx.TimeoutException, httpx.ConnectError):
                duration_ms = int((perf_counter() - start) * 1000)
                logger.exception(
                    "openai_request_failed",
                    extra={
                        "event": "openai_request_failed",
                        "route": "/v1/responses",
                        "duration_ms": duration_ms,
                        "model": payload.get("model"),
                        "error_type": "timeout_or_connection",
                    },
                )
                raise

        duration_ms = int((perf_counter() - start) * 1000)
        logger.info(
            "openai_request_completed",
            extra={
                "event": "openai_request_completed",
                "route": "/v1/responses",
                "duration_ms": duration_ms,
                "model": payload.get("model"),
                "status_code": response.status_code,
            },
        )

        if response.status_code >= 500:
            raise httpx.TimeoutException(f"OpenAI upstream server error: {response.status_code}")

        if response.status_code >= 400:
            raise ProviderError(f"OpenAI API error ({response.status_code}): {response.text}")

        return response.json()

    @staticmethod
    def _extract_output_text(response_payload: dict[str, Any]) -> str:
        output_text = response_payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        chunks: list[str] = []
        for item in response_payload.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        text_payload = "\n".join(chunks).strip()
        if text_payload:
            return text_payload
        raise ProviderError("OpenAI response did not include structured text output")

    async def generate_structured(
        self,
        *,
        prompt: str,
        schema_name: str,
        schema: dict,
        max_output_tokens: int,
    ) -> ProviderResult:
        payload = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        }

        response_payload = await self._call_responses(payload)
        output_text = self._extract_output_text(response_payload)

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Model returned invalid JSON: {exc}") from exc

        usage = response_payload.get("usage", {})
        prompt_tokens = usage.get("input_tokens")
        completion_tokens = usage.get("output_tokens")

        return ProviderResult(
            data=parsed,
            model=response_payload.get("model") or self.model,
            tokens_prompt=prompt_tokens if isinstance(prompt_tokens, int) else None,
            tokens_completion=completion_tokens if isinstance(completion_tokens, int) else None,
        )
