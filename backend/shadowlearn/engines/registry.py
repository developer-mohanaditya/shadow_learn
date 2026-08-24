from __future__ import annotations

from .base import SpeechEngine
from .local_models import ChatterboxEngine, KokoroEngine
from .system import SystemSpeechEngine
from .zonos import ZonosEngine


class EngineRegistry:
    def __init__(self):
        self.engines: dict[str, SpeechEngine] = {
            "chatterbox": ChatterboxEngine(),
            "zonos2": ZonosEngine(),
            "kokoro": KokoroEngine(),
            "system": SystemSpeechEngine(),
        }

    def get(self, engine_id: str) -> SpeechEngine:
        if engine_id not in self.engines:
            raise KeyError(f"Unknown engine: {engine_id}")
        return self.engines[engine_id]

    def health(self) -> list[dict]:
        return [vars(engine.health()) for engine in self.engines.values()]

    def close(self) -> None:
        for engine in self.engines.values():
            engine.close()


registry = EngineRegistry()

