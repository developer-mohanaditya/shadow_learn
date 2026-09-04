from __future__ import annotations

import base64
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from threading import Event, Lock, RLock
from typing import Any

from ..config import settings
from .base import EngineHealth, SpeechEngine


class ZonosEngine(SpeechEngine):
    id = "zonos2"
    name = "ZONOS2 Metal"
    _default_voice_labels = {
        "zonos2-american-female": "AmericanFemale",
        "zonos2-american-male": "AmericanMale",
        "zonos2-british-female": "BritishFemale",
    }

    def __init__(self) -> None:
        self._speaker_ids: dict[str, str] = {}
        self._speaker_lock = Lock()
        self._server_lock = RLock()
        self._server_process: subprocess.Popen[bytes] | None = None
        self._session_id = "shadow-learn"

    def health(self) -> EngineHealth:
        running = self._server_healthy()
        installed = self._launcher_path().is_file()
        available = running or installed
        if running:
            reason = None
        elif installed:
            reason = "Starts locally when selected; no model memory is reserved while idle"
        else:
            reason = "ZONOS2 is not installed"
        return EngineHealth(
            id=self.id,
            name=self.name,
            available=available,
            reason=reason,
            capabilities={"voice_cloning": True, "presets": True, "accents": ["us", "uk"]},
        )

    def prepare(self) -> None:
        with self._server_lock:
            if self._server_healthy():
                return
            launcher = self._launcher_path()
            if not launcher.is_file():
                raise RuntimeError("ZONOS2 is not installed")
            engine_dir = launcher.parent
            log = (settings.data / "zonos2.log").open("ab")
            error_log = (settings.data / "zonos2-error.log").open("ab")
            try:
                self._server_process = subprocess.Popen(
                    [
                        str(launcher), "--quant", "q4_k", "--gpu", "--yes", "--no-browser",
                        "--", "--dac-gpu",
                    ],
                    cwd=engine_dir,
                    stdout=log,
                    stderr=error_log,
                    start_new_session=True,
                )
            finally:
                log.close()
                error_log.close()
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self._server_healthy():
                    return
                if self._server_process.poll() is not None:
                    break
                time.sleep(0.5)
            self.release()
            raise RuntimeError("ZONOS2 did not become ready within two minutes; check data/zonos2-error.log")

    def release(self) -> None:
        with self._server_lock:
            process = self._server_process
            self._server_process = None
            self._speaker_ids.clear()
            if not process or process.poll() is not None:
                return
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)

    def close(self) -> None:
        self.release()

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
        payload: dict[str, Any] = {
            "text": text,
            "stream": False,
            "format": "wav",
            "seed": int(options.get("seed", 42)),
        }
        pace = float(options.get("pace", 1))
        if pace != 1:
            payload.update({"speaking_rate_enabled": True, "speed": pace})
        speaker_key = None
        if voice and voice.get("processed_path"):
            speaker_key = str(voice.get("id") or voice["processed_path"])
            payload["speaker_embedding_id"] = self._ensure_speaker(speaker_key, voice)
        elif voice and voice.get("id") in self._default_voice_labels:
            payload["speaker_embedding_id"] = self._default_speaker_id(
                self._default_voice_labels[voice["id"]]
            )
        for attempt in range(2):
            request = urllib.request.Request(
                f"{settings.zonos_url}/tts/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "X-TTS-Session-ID": self._session_id},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=1800) as response:
                    output.write_bytes(response.read())
                return
            except urllib.error.HTTPError as exc:
                if attempt == 0 and speaker_key and exc.code == 400:
                    self._speaker_ids.pop(speaker_key, None)
                    payload["speaker_embedding_id"] = self._ensure_speaker(speaker_key, voice)
                    continue
                detail = exc.read().decode(errors="replace")
                raise RuntimeError(f"ZONOS2 generation failed: {detail}") from exc

    def _ensure_speaker(self, key: str, voice: dict[str, Any]) -> str:
        with self._speaker_lock:
            if key in self._speaker_ids:
                return self._speaker_ids[key]
            path = Path(voice["processed_path"])
            payload = {
                "label": voice.get("name") or "Shadow Learn voice",
                "speaker_audio_name": path.name,
                "speaker_audio_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
            request = urllib.request.Request(
                f"{settings.zonos_url}/tts/speakers",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "X-TTS-Session-ID": self._session_id},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=300) as response:
                speaker_id = json.loads(response.read())["id"]
            self._speaker_ids[key] = speaker_id
            return speaker_id

    def _default_speaker_id(self, label: str) -> str:
        request = urllib.request.Request(f"{settings.zonos_url}/tts/speakers")
        with urllib.request.urlopen(request, timeout=10) as response:
            speakers = json.loads(response.read()).get("speakers", [])
        for speaker in speakers:
            if speaker.get("is_default") and speaker.get("label") == label:
                return str(speaker["id"])
        raise RuntimeError(f"ZONOS2 default voice is unavailable: {label}")

    @staticmethod
    def _launcher_path() -> Path:
        return settings.root / ".engines" / "zonos2" / "start-zonos2.sh"

    @staticmethod
    def _server_healthy() -> bool:
        try:
            with urllib.request.urlopen(f"{settings.zonos_url}/health", timeout=1) as response:
                return response.status < 400
        except (OSError, urllib.error.URLError):
            return False
