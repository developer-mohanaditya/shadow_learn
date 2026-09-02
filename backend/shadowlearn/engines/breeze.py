from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Any

from .base import EngineHealth, SpeechEngine
from .worker import JsonWorker


class BreezeEngine(SpeechEngine):
    id = "breeze"
    name = "Breeze TTS 2 · MLX"

    def __init__(self) -> None:
        self.worker = JsonWorker(self.id)

    def health(self) -> EngineHealth:
        available, reason = self.worker.available()
        return EngineHealth(
            id=self.id,
            name=self.name,
            available=available,
            reason=reason,
            capabilities={
                "voice_cloning": True,
                "voice_design": True,
                "voice_direction": True,
                "streaming": True,
                "vocal_events": ["laugh", "sigh", "cough", "clears throat"],
                "languages": ["en", "zh"],
                "model_variants": ["mixed-4bit"],
            },
        )

    def synthesize(
        self,
        text: str,
        output: Path,
        voice: dict[str, Any] | None,
        options: dict[str, Any],
        cancelled: Event,
    ) -> None:
        if cancelled.is_set():
            raise InterruptedError("Generation cancelled")
        self.worker.request(
            {"text": text, "output": str(output), "voice": voice, "options": options},
            timeout=3600,
        )

    def close(self) -> None:
        self.worker.close()


breeze_engine = BreezeEngine()
