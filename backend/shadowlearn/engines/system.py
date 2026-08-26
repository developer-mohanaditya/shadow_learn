from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from threading import Event
from typing import Any

from .base import EngineHealth, SpeechEngine


class SystemSpeechEngine(SpeechEngine):
    id = "system"
    name = "macOS Development Voice"

    def health(self) -> EngineHealth:
        available = bool(shutil.which("say") and shutil.which("afconvert"))
        return EngineHealth(
            id=self.id,
            name=self.name,
            available=available,
            reason=None if available else "macOS say/afconvert not found",
            capabilities={
                "voice_cloning": False,
                "presets": True,
                "accents": ["us", "uk", "in", "au", "ie", "za"],
                "development_only": True,
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
        aiff = output.with_suffix(".aiff.part")
        name = str((voice or {}).get("name") or "").removesuffix(" (macOS)")
        if not name:
            name = "Daniel" if (voice or {}).get("accent") == "uk" else "Samantha"
        pace = float(options.get("pace", 1.0))
        rate = max(90, min(260, round(175 * pace)))
        subprocess.run(
            ["/usr/bin/say", "-v", name, "-r", str(rate), "-o", str(aiff), text],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@24000", str(aiff), str(output)],
            check=True,
            capture_output=True,
        )
        aiff.unlink(missing_ok=True)
