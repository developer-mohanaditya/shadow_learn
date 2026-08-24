from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from threading import Event, Lock
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from .audio import combine, duration, normalize_reference
from .config import settings
from .database import db, decode_json_fields, now_iso
from .engines import registry
from .jobs import jobs
from .schemas import GenerationCreate, VoiceUpdate
from .text import normalize_text, speech_text, split_phrases


router = APIRouter(prefix="/api")
VOICE_PREVIEW_TEXT = (
    "The morning air feels crisp and bright. Take a steady breath, speak clearly, "
    "and let every sentence flow naturally."
)
voice_preview_lock = Lock()


def generation_detail(generation_id: str) -> dict:
    row = db.fetch_one("SELECT * FROM generations WHERE id=?", (generation_id,))
    if not row:
        raise HTTPException(404, "Generation not found")
    row = decode_json_fields(row)
    row["phrases"] = db.fetch_all(
        "SELECT phrase_index,text,source_start,source_end,pause_after_ms,start_time,end_time,status FROM phrases WHERE generation_id=? ORDER BY phrase_index",
        (generation_id,),
    )
    row["audio"] = {
        "wav": f"/api/generations/{generation_id}/audio/wav" if row.get("wav_path") else None,
        "mp3": f"/api/generations/{generation_id}/audio/mp3" if row.get("mp3_path") else None,
    }
    return row


@router.post("/generations", status_code=202)
def create_generation(payload: GenerationCreate) -> dict:
    normalized = normalize_text(payload.text)
    phrases = split_phrases(normalized)
    if not phrases:
        raise HTTPException(422, "The script contains no speakable text")
    try:
        engine_health = registry.get(payload.engine).health()
    except KeyError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not engine_health.available:
        raise HTTPException(409, engine_health.reason or "Selected engine is unavailable")
    voice = None
    if payload.voice_id:
        voice = db.fetch_one("SELECT * FROM voices WHERE id=?", (payload.voice_id,))
        if not voice:
            raise HTTPException(422, "Voice not found")
        if voice["engine"] != payload.engine:
            raise HTTPException(422, "Voice is incompatible with the selected engine")
    generation_id = str(uuid4())
    timestamp = now_iso()
    title = payload.title or speech_text(normalized)[:60].split("\n", 1)[0]
    options = payload.model_dump(exclude={"text", "title", "engine", "voice_id"})
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO generations(id,title,raw_text,normalized_text,engine,voice_id,settings_json,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,'queued',?,?)",
            (
                generation_id, title, payload.text, normalized, payload.engine, payload.voice_id,
                json.dumps(options), timestamp, timestamp,
            ),
        )
        connection.executemany(
            "INSERT INTO phrases(generation_id,phrase_index,text,source_start,source_end,pause_after_ms) VALUES (?,?,?,?,?,?)",
            [
                (generation_id, phrase.index, phrase.text, phrase.source_start, phrase.source_end, phrase.pause_after_ms)
                for phrase in phrases
            ],
        )
    jobs.enqueue(generation_id)
    return generation_detail(generation_id)


@router.get("/generations")
def list_generations(
    q: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
) -> dict:
    where, params = "", []
    if q:
        where = "WHERE title LIKE ? OR raw_text LIKE ?"
        params.extend([f"%{q}%", f"%{q}%"])
    count = db.fetch_one(f"SELECT COUNT(*) AS count FROM generations {where}", tuple(params))["count"]
    rows = db.fetch_all(
        f"SELECT id,title,engine,voice_id,status,progress,error,duration,created_at,updated_at,wav_path,mp3_path FROM generations {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params + [page_size, (page - 1) * page_size]),
    )
    for row in rows:
        row["audio"] = {
            "wav": f"/api/generations/{row['id']}/audio/wav" if row.pop("wav_path") else None,
            "mp3": f"/api/generations/{row['id']}/audio/mp3" if row.pop("mp3_path") else None,
        }
    return {"items": rows, "total": count, "page": page, "page_size": page_size}


@router.get("/generations/{generation_id}")
def get_generation(generation_id: str) -> dict:
    return generation_detail(generation_id)


@router.get("/generations/{generation_id}/events")
async def generation_events(generation_id: str):
    generation_detail(generation_id)

    async def stream():
        revision = -1
        while True:
            revision = await asyncio.to_thread(jobs.wait, generation_id, revision, 15)
            current = generation_detail(generation_id)
            yield f"data: {json.dumps(current)}\n\n"
            if current["status"] in {"complete", "failed", "cancelled"}:
                return

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/generations/{generation_id}/cancel")
def cancel_generation(generation_id: str) -> dict:
    generation_detail(generation_id)
    if not jobs.cancel(generation_id):
        raise HTTPException(409, "Generation is not currently running")
    return {"ok": True}


@router.post("/generations/{generation_id}/resume", status_code=202)
def resume_generation(generation_id: str) -> dict:
    row = generation_detail(generation_id)
    if row["status"] not in {"interrupted", "failed", "cancelled"}:
        raise HTTPException(409, "Only interrupted, failed, or cancelled jobs can be resumed")
    db.execute(
        "UPDATE generations SET status='queued',error=NULL,updated_at=? WHERE id=?",
        (now_iso(), generation_id),
    )
    jobs.enqueue(generation_id)
    return generation_detail(generation_id)


@router.delete("/generations/{generation_id}", status_code=204)
def delete_generation(generation_id: str):
    row = db.fetch_one("SELECT * FROM generations WHERE id=?", (generation_id,))
    if not row:
        raise HTTPException(404, "Generation not found")
    if row["status"] == "processing":
        raise HTTPException(409, "Cancel the active generation before deleting it")
    folder = settings.audio / generation_id
    db.execute("DELETE FROM generations WHERE id=?", (generation_id,))
    shutil.rmtree(folder, ignore_errors=True)


@router.get("/generations/{generation_id}/audio/{audio_format}")
def generation_audio(generation_id: str, audio_format: str):
    if audio_format not in {"wav", "mp3"}:
        raise HTTPException(404, "Unsupported format")
    row = db.fetch_one("SELECT wav_path,mp3_path FROM generations WHERE id=?", (generation_id,))
    if not row:
        raise HTTPException(404, "Generation not found")
    path = Path(row[f"{audio_format}_path"] or "")
    if not path.is_file():
        raise HTTPException(404, "Audio artifact is missing")
    media_type = "audio/wav" if audio_format == "wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/voices")
def list_voices() -> list[dict]:
    return db.fetch_all("SELECT * FROM voices ORDER BY kind DESC,name")


@router.post("/voices/{voice_id}/preview")
def create_voice_preview(voice_id: str) -> dict:
    voice = db.fetch_one("SELECT * FROM voices WHERE id=?", (voice_id,))
    if not voice:
        raise HTTPException(404, "Voice not found")
    try:
        engine = registry.get(voice["engine"])
    except KeyError as exc:
        raise HTTPException(422, str(exc)) from exc
    health = engine.health()
    if not health.available:
        raise HTTPException(409, health.reason or "Voice engine is unavailable")
    folder = settings.voices / voice_id
    wav_target = folder / "preview.wav"
    mp3_target = folder / "preview.mp3"
    cached = mp3_target.is_file() and wav_target.is_file()
    if not cached:
        with voice_preview_lock:
            cached = mp3_target.is_file() and wav_target.is_file()
            if not cached:
                folder.mkdir(parents=True, exist_ok=True, mode=0o700)
                temporary = settings.temporary / f"voice-preview-{uuid4()}"
                temporary.mkdir(parents=True, mode=0o700)
                phrase = temporary / "phrase.wav"
                try:
                    engine.synthesize(
                        VOICE_PREVIEW_TEXT,
                        phrase,
                        voice,
                        {"accent": voice["accent"], "pace": 1.0, "mood": "friendly", "expressiveness": 0.5},
                        Event(),
                    )
                    combine([phrase], wav_target, mp3_target)
                except Exception as exc:
                    raise HTTPException(502, f"Voice preview failed: {exc}") from exc
                finally:
                    shutil.rmtree(temporary, ignore_errors=True)
    return {
        "voice_id": voice_id,
        "text": VOICE_PREVIEW_TEXT,
        "audio_url": f"/api/voices/{voice_id}/preview/audio",
        "cached": cached,
    }


@router.get("/voices/{voice_id}/preview/audio")
def voice_preview_audio(voice_id: str):
    if not db.fetch_one("SELECT id FROM voices WHERE id=?", (voice_id,)):
        raise HTTPException(404, "Voice not found")
    path = settings.voices / voice_id / "preview.mp3"
    if not path.is_file():
        raise HTTPException(404, "Generate the voice preview first")
    return FileResponse(path, media_type="audio/mpeg", filename=f"{voice_id}-preview.mp3")


@router.post("/voices", status_code=201)
def create_voice(
    name: str = Form(...),
    engine: str = Form("chatterbox"),
    accent: str = Form("us"),
    consented: bool = Form(...),
    audio: UploadFile = File(...),
) -> dict:
    if not consented:
        raise HTTPException(422, "Voice ownership or permission must be acknowledged")
    try:
        selected_engine = registry.get(engine).health()
    except KeyError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not selected_engine.capabilities.get("voice_cloning"):
        raise HTTPException(422, f"{selected_engine.name} does not support voice cloning")
    suffix = Path(audio.filename or "voice.wav").suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a"}:
        raise HTTPException(415, "Use a WAV, MP3, or M4A recording")
    voice_id = str(uuid4())
    folder = settings.voices / voice_id
    folder.mkdir(parents=True, mode=0o700)
    source = folder / f"original{suffix}"
    with source.open("wb") as output:
        shutil.copyfileobj(audio.file, output)
    processed = folder / "reference.wav"
    try:
        normalize_reference(source, processed)
        seconds = duration(processed)
        if seconds < 10 or seconds > 30:
            raise HTTPException(422, f"Processed recording is {seconds:.1f}s; provide 10–30 seconds")
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    timestamp = now_iso()
    db.execute(
        "INSERT INTO voices(id,name,engine,accent,kind,original_path,processed_path,consented,created_at,updated_at) VALUES (?,?,?,?, 'cloned',?,?,1,?,?)",
        (voice_id, name, engine, accent, str(source), str(processed), timestamp, timestamp),
    )
    return db.fetch_one("SELECT * FROM voices WHERE id=?", (voice_id,))


@router.patch("/voices/{voice_id}")
def update_voice(voice_id: str, payload: VoiceUpdate) -> dict:
    row = db.fetch_one("SELECT * FROM voices WHERE id=?", (voice_id,))
    if not row:
        raise HTTPException(404, "Voice not found")
    db.execute("UPDATE voices SET name=?,updated_at=? WHERE id=?", (payload.name, now_iso(), voice_id))
    return db.fetch_one("SELECT * FROM voices WHERE id=?", (voice_id,))


@router.delete("/voices/{voice_id}", status_code=204)
def delete_voice(voice_id: str):
    row = db.fetch_one("SELECT * FROM voices WHERE id=?", (voice_id,))
    if not row:
        raise HTTPException(404, "Voice not found")
    if row["kind"] == "preset":
        raise HTTPException(409, "Preset voices cannot be deleted")
    db.execute("DELETE FROM voices WHERE id=?", (voice_id,))
    shutil.rmtree(settings.voices / voice_id, ignore_errors=True)


@router.get("/engines")
def engines() -> list[dict]:
    return registry.health()


@router.post("/backups", status_code=201)
def create_backup() -> dict:
    return db.create_backup()


@router.get("/backups")
def list_backups() -> list[dict]:
    return db.fetch_all("SELECT * FROM backups ORDER BY created_at DESC")


@router.post("/backups/{backup_id}/restore")
def restore_backup(backup_id: str) -> dict:
    if db.fetch_one("SELECT COUNT(*) AS count FROM generations WHERE status='processing'")["count"]:
        raise HTTPException(409, "Cannot restore while generation is active")
    try:
        db.restore_backup(backup_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"ok": True, "restart_required": True}


@router.get("/system/health")
def system_health() -> dict:
    integrity = db.fetch_one("PRAGMA integrity_check")
    disk = shutil.disk_usage(settings.data)
    backup = db.fetch_one("SELECT * FROM backups ORDER BY created_at DESC LIMIT 1")
    return {
        "database": next(iter(integrity.values())) if integrity else "unknown",
        "data_directory": str(settings.data),
        "disk_free": disk.free,
        "last_backup": backup,
        "engines": registry.health(),
    }
