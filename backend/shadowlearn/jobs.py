from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from uuid import uuid4

from .audio import combine, create_silence, duration
from .config import settings
from .database import db, now_iso
from .engines import registry


class JobManager:
    def __init__(self):
        self.queue: queue.Queue[str | None] = queue.Queue()
        self.cancellations: dict[str, threading.Event] = {}
        self.events: dict[str, threading.Condition] = {}
        self.revisions: dict[str, int] = {}
        self.thread: threading.Thread | None = None
        self.running = False

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="shadow-generation-worker", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        self.queue.put(None)
        if self.thread:
            self.thread.join(timeout=15)
        registry.close()

    def enqueue(self, generation_id: str) -> None:
        self.cancellations[generation_id] = threading.Event()
        self.events.setdefault(generation_id, threading.Condition())
        self.queue.put(generation_id)
        self._notify(generation_id)

    def cancel(self, generation_id: str) -> bool:
        event = self.cancellations.get(generation_id)
        if event:
            event.set()
            return True
        return False

    def revision(self, generation_id: str) -> int:
        return self.revisions.get(generation_id, 0)

    def wait(self, generation_id: str, revision: int, timeout: float = 15) -> int:
        condition = self.events.setdefault(generation_id, threading.Condition())
        with condition:
            if self.revision(generation_id) <= revision:
                condition.wait(timeout)
        return self.revision(generation_id)

    def _notify(self, generation_id: str) -> None:
        self.revisions[generation_id] = self.revision(generation_id) + 1
        condition = self.events.setdefault(generation_id, threading.Condition())
        with condition:
            condition.notify_all()

    def _loop(self) -> None:
        while self.running:
            generation_id = self.queue.get()
            if generation_id is None:
                return
            try:
                self._process(generation_id)
            except Exception as exc:
                db.execute(
                    "UPDATE generations SET status='failed',error=?,updated_at=? WHERE id=?",
                    (str(exc), now_iso(), generation_id),
                )
            finally:
                self._release_generation_engine(generation_id)
                self._notify(generation_id)

    @staticmethod
    def _release_generation_engine(generation_id: str) -> None:
        generation = db.fetch_one("SELECT engine FROM generations WHERE id=?", (generation_id,))
        if generation:
            registry.get(generation["engine"]).release()

    def _process(self, generation_id: str) -> None:
        generation = db.fetch_one("SELECT * FROM generations WHERE id=?", (generation_id,))
        if not generation:
            return
        options = json.loads(generation["settings_json"])
        engine = registry.get(generation["engine"])
        engine.prepare()
        health = engine.health()
        if not health.available:
            raise RuntimeError(health.reason or f"{health.name} is unavailable")
        voice = None
        if generation["voice_id"]:
            voice = db.fetch_one("SELECT * FROM voices WHERE id=?", (generation["voice_id"],))
        cancellation = self.cancellations.setdefault(generation_id, threading.Event())
        db.execute(
            "UPDATE generations SET status='processing',error=NULL,updated_at=? WHERE id=?",
            (now_iso(), generation_id),
        )
        self._notify(generation_id)
        phrases = db.fetch_all(
            "SELECT * FROM phrases WHERE generation_id=? ORDER BY phrase_index", (generation_id,)
        )
        output_dir = settings.audio / generation_id
        output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        elapsed = 0.0
        parts: list[Path] = []
        for index, phrase in enumerate(phrases):
            if cancellation.is_set():
                db.execute(
                    "UPDATE generations SET status='cancelled',updated_at=? WHERE id=?",
                    (now_iso(), generation_id),
                )
                return
            phrase_path = output_dir / f"phrase-{index:04d}.wav"
            if phrase["status"] == "complete" and phrase["artifact_path"] and Path(phrase["artifact_path"]).exists():
                phrase_path = Path(phrase["artifact_path"])
                phrase_duration = duration(phrase_path)
            else:
                partial = settings.temporary / f"{generation_id}-{index}-{uuid4().hex}.wav"
                engine.synthesize(phrase["text"], partial, voice, options, cancellation)
                partial.replace(phrase_path)
                phrase_duration = duration(phrase_path)
            start_time = elapsed
            elapsed += phrase_duration
            parts.append(phrase_path)
            if phrase["pause_after_ms"]:
                silence = output_dir / f"pause-{index:04d}.wav"
                create_silence(silence, phrase["pause_after_ms"])
                parts.append(silence)
                elapsed += phrase["pause_after_ms"] / 1000
            with db.transaction() as connection:
                connection.execute(
                    "UPDATE phrases SET status='complete',start_time=?,end_time=?,artifact_path=? WHERE id=?",
                    (start_time, start_time + phrase_duration, str(phrase_path), phrase["id"]),
                )
                connection.execute(
                    "UPDATE generations SET progress=?,updated_at=? WHERE id=?",
                    ((index + 1) / len(phrases), now_iso(), generation_id),
                )
            self._notify(generation_id)
        wav_path = output_dir / "generation.wav"
        mp3_path = output_dir / "generation.mp3"
        combine(parts, wav_path, mp3_path)
        total_duration = duration(wav_path)
        db.execute(
            "UPDATE generations SET status='complete',progress=1,wav_path=?,mp3_path=?,duration=?,error=NULL,updated_at=? WHERE id=?",
            (str(wav_path), str(mp3_path), total_duration, now_iso(), generation_id),
        )


jobs = JobManager()
