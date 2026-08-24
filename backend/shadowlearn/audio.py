from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path


def require_ffmpeg() -> str:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("FFmpeg is required. Run: brew install ffmpeg")
    return executable


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as stream:
        return stream.getnframes() / float(stream.getframerate())


def create_silence(path: Path, milliseconds: int, rate: int = 24000) -> None:
    frames = int(rate * milliseconds / 1000)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(b"\0\0" * frames)


def combine(parts: list[Path], wav_target: Path, mp3_target: Path) -> None:
    ffmpeg = require_ffmpeg()
    manifest = wav_target.with_suffix(".concat.txt")
    manifest.write_text("".join(f"file '{_escape(path)}'\n" for path in parts), encoding="utf-8")
    wav_partial = wav_target.with_suffix(".wav.part")
    mp3_partial = mp3_target.with_suffix(".mp3.part")
    try:
        subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                "-i", str(manifest), "-ac", "1", "-ar", "24000", "-af", "loudnorm=I=-18:TP=-2:LRA=11",
                "-c:a", "pcm_s16le", "-f", "wav", str(wav_partial),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav_partial),
                "-codec:a", "libmp3lame", "-q:a", "3", "-f", "mp3", str(mp3_partial),
            ],
            check=True,
            capture_output=True,
        )
        wav_partial.replace(wav_target)
        mp3_partial.replace(mp3_target)
    finally:
        manifest.unlink(missing_ok=True)
        wav_partial.unlink(missing_ok=True)
        mp3_partial.unlink(missing_ok=True)


def normalize_reference(source: Path, target: Path) -> None:
    ffmpeg = require_ffmpeg()
    partial = target.with_suffix(".wav.part")
    subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-af",
            "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-45dB:stop_periods=1:stop_duration=0.2:stop_threshold=-45dB,loudnorm=I=-18:TP=-2:LRA=9",
            "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", "-f", "wav", str(partial),
        ],
        check=True,
        capture_output=True,
    )
    partial.replace(target)


def _escape(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")

