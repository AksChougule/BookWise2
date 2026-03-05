from pathlib import Path

import pytest

from app.services.prompt_store import PromptCompileError, PromptStore


def test_prompt_store_renders_and_hashes(tmp_path: Path) -> None:
    template = tmp_path / "sample.txt"
    template.write_text("Title: {{ title }}\\nAuthor: {{ author }}\\n", encoding="utf-8")

    store = PromptStore(tmp_path)
    result = store.render("sample", {"title": "Deep Work", "author": "Cal Newport"})

    assert "Deep Work" in result.compiled_prompt
    assert "Cal Newport" in result.compiled_prompt
    assert len(result.prompt_hash) == 64
    assert result.prompt_version


def test_prompt_store_strict_undefined_raises(tmp_path: Path) -> None:
    template = tmp_path / "sample.txt"
    template.write_text("Title: {{ title }}\\nAuthor: {{ author }}\\n", encoding="utf-8")

    store = PromptStore(tmp_path)

    with pytest.raises(PromptCompileError) as exc:
        store.render("sample", {"title": "Deep Work"})

    assert "prompt rendering failed" in str(exc.value).lower()
