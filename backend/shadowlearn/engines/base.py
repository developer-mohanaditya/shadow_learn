from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any


@dataclass
class EngineHealth:
    id: str
    name: str
    available: bool
    reason: str | None
    capabilities: dict[str, Any]


class SpeechEngine(ABC):
    id: str
    name: str

    @abstractmethod
    def health(self) -> EngineHealth: ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output: Path,
        voice: dict[str, Any] | None,
        options: dict[str, Any],
        cancelled: Event,
    ) -> None: ...

    def close(self) -> None:
        return None

