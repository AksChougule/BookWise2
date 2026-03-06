from __future__ import annotations

import hashlib
import re


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    collapsed = re.sub(r"\s+", " ", value.strip())
    return collapsed.lower()


def compute_input_fingerprint(*, title: str | None, authors: str | None, description: str | None) -> str:
    payload = "|".join([_normalize_text(title), _normalize_text(authors), _normalize_text(description)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_idempotency_key(*, work_id: str, section: str, prompt_hash: str, model: str) -> str:
    payload = "|".join([work_id, section, prompt_hash, model])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
