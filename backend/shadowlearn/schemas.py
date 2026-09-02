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


class BreezeGenerationCreate(BaseModel):
    text: str = Field(min_length=1, max_length=25_000)
    title: str | None = Field(default=None, max_length=120)
    mode: Literal["design", "clone", "direction"] = "design"
    language: Literal["en", "zh"] = "en"
    accent_direction: str = Field(default="Neutral international English", max_length=160)
    voice_id: str | None = None
    voice_description: str = Field(default="", max_length=800)
    direction: str = Field(default="Speak clearly and naturally.", max_length=1200)
    model_variant: Literal["mixed-4bit"] = "mixed-4bit"
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    cfg_scale: float = Field(default=4.0, gt=0, le=10)
    temperature: float = Field(default=0.9, gt=0, le=2)
    top_k: int = Field(default=50, ge=1, le=500)
    top_p: float = Field(default=1.0, gt=0, le=1)
    repetition_penalty: float = Field(default=1.1, gt=0, le=2)
    chunk_frames: int = Field(default=4, ge=1, le=16)
    max_new_tokens: int = Field(default=1500, ge=64, le=4096)


class BreezeDesignedVoiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    language: Literal["en", "zh"] = "en"
    accent_direction: str = Field(default="", max_length=160)
    description: str = Field(min_length=10, max_length=800)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    cfg_scale: float = Field(default=4.0, gt=0, le=10)


class BreezePreviewCreate(BaseModel):
    text: str = Field(
        default="The morning air feels crisp and bright. Take a steady breath and speak clearly.",
        min_length=1,
        max_length=500,
    )
    direction: str = Field(default="Speak clearly and naturally.", max_length=800)
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
