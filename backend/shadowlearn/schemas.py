from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GenerationCreate(BaseModel):
    text: str = Field(min_length=1, max_length=25_000)
    title: str | None = Field(default=None, max_length=120)
    engine: str = "kokoro"
    voice_id: str | None = None
    accent: Literal["us", "uk"] = "us"
    pace: float = Field(default=1.0, ge=0.75, le=1.25)
    mood: Literal["neutral", "friendly", "formal", "cheerful", "serious", "dramatic"] = "neutral"
    expressiveness: float = Field(default=0.5, ge=0, le=1.5)
    cfg_weight: float = Field(default=0.5, ge=0, le=1)


class VoiceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
