from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Any

from .base import EngineHealth, SpeechEngine
from .worker import JsonWorker


class WorkerSpeechEngine(SpeechEngine):
    def __init__(self, engine_id: str, name: str, cloning: bool, presets: bool):
        self.id = engine_id
        self.name = name
        self.worker = JsonWorker(engine_id)
        self.cloning = cloning
        self.presets = presets

    def health(self) -> EngineHealth:
        available, reason = self.worker.available()
        return EngineHealth(
            id=self.id,
            name=self.name,
            available=available,
            reason=reason,
            capabilities={
                "voice_cloning": self.cloning,
                "presets": self.presets,
                "accents": ["us", "uk"],
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
            {"text": text, "output": str(output), "voice": voice, "options": options}
        )

    def close(self) -> None:
        self.worker.close()


class ChatterboxEngine(WorkerSpeechEngine):
    def __init__(self):
        super().__init__("chatterbox", "Chatterbox", cloning=True, presets=False)


class KokoroEngine(WorkerSpeechEngine):
    def __init__(self):
        super().__init__("kokoro", "Kokoro MLX", cloning=False, presets=True)

