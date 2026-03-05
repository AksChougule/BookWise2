from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError


class PromptCompileError(Exception):
    error_type = "prompt_compile_error"

    def __init__(self, prompt_name: str, message: str):
        self.prompt_name = prompt_name
        super().__init__(message)


@dataclass(slots=True)
class PromptRenderResult:
    compiled_prompt: str
    prompt_version: str
    prompt_hash: str


class PromptStore:
    def __init__(self, prompt_dir: Path):
        self.prompt_dir = prompt_dir
        self.environment = Environment(
            loader=FileSystemLoader(str(prompt_dir)),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=False,
            lstrip_blocks=False,
        )

    def render(self, prompt_name: str, context: dict[str, str]) -> PromptRenderResult:
        template_filename = f"{prompt_name}.txt"
        template_path = self.prompt_dir / template_filename
        if not template_path.exists():
            raise PromptCompileError(prompt_name, f"Prompt template not found: {template_filename}")

        try:
            template = self.environment.get_template(template_filename)
            compiled_prompt = template.render(**context)
        except TemplateError as exc:
            raise PromptCompileError(prompt_name, f"Prompt rendering failed: {exc}") from exc

        prompt_hash = hashlib.sha256(compiled_prompt.encode("utf-8")).hexdigest()
        prompt_version = datetime.fromtimestamp(template_path.stat().st_mtime, tz=UTC).isoformat()
        return PromptRenderResult(
            compiled_prompt=compiled_prompt,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
        )
