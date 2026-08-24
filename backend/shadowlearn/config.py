from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path
    data: Path
    database: Path
    audio: Path
    voices: Path
    uploads: Path
    models: Path
    backups: Path
    temporary: Path
    frontend_dist: Path
    max_characters: int = 25_000
    zonos_url: str = "http://127.0.0.1:1919"

    @classmethod
    def load(cls) -> "Settings":
        root = Path(__file__).resolve().parents[2]
        data = Path(os.environ.get("SHADOW_LEARN_DATA", root / "data")).expanduser().resolve()
        result = cls(
            root=root,
            data=data,
            database=data / "shadowing.db",
            audio=data / "audio",
            voices=data / "voices",
            uploads=data / "uploads",
            models=data / "models",
            backups=data / "backups",
            temporary=data / "tmp",
            frontend_dist=root / "frontend" / "dist",
            zonos_url=os.environ.get("SHADOW_LEARN_ZONOS_URL", "http://127.0.0.1:1919"),
        )
        result.ensure_directories()
        return result

    def ensure_directories(self) -> None:
        for path in (
            self.data,
            self.audio,
            self.voices,
            self.uploads,
            self.models,
            self.backups,
            self.temporary,
        ):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)


settings = Settings.load()

