from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GenerationStatusOut(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class SectionOut(StrEnum):
    KEY_IDEAS = "key_ideas"
    CRITIQUE = "critique"


class KeyIdeasPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_ideas: str = Field(min_length=1)


class CritiquePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strengths: str = Field(min_length=1)
    weaknesses: str = Field(min_length=1)
    who_should_read: str = Field(min_length=1)


class GenerationMeta(BaseModel):
    work_id: str
    status: GenerationStatusOut
    section: SectionOut
    error_message: str | None = None
    model: str | None = None
    tokens_prompt: int | None = None
    tokens_completion: int | None = None
    generation_time_ms: int | None = None
    updated_at: datetime


class KeyIdeasOut(GenerationMeta):
    section: SectionOut = SectionOut.KEY_IDEAS
    key_ideas: str | None = None


class CritiqueOut(GenerationMeta):
    section: SectionOut = SectionOut.CRITIQUE
    strengths: str | None = None
    weaknesses: str | None = None
    who_should_read: str | None = None
