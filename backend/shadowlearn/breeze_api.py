from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from threading import Event
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from .api import audio_download_name
from .audio import duration, normalize_reference
from .breeze_jobs import breeze_jobs
from .config import settings
from .database import db, decode_json_fields, now_iso
from .engines.breeze import breeze_engine
from .schemas import BreezeDesignedVoiceCreate, BreezeGenerationCreate, BreezePreviewCreate
from .text import normalize_text, speech_text, split_phrases


router = APIRouter(prefix="/api/v2")


def generation_detail(generation_id: str) -> dict:
    row = db.fetch_one("SELECT * FROM breeze_generations WHERE id=?", (generation_id,))
    if not row:
        raise HTTPException(404, "Breeze generation not found")
    row = decode_json_fields(row)
    row["phrases"] = db.fetch_all(
        "SELECT phrase_index,text,source_start,source_end,pause_after_ms,start_time,"
        "end_time,status FROM breeze_phrases WHERE generation_id=? ORDER BY phrase_index",
        (generation_id,),
    )
    row["audio"] = {
        "wav": f"/api/v2/generations/{generation_id}/audio/wav" if row.get("wav_path") else None,
        "mp3": f"/api/v2/generations/{generation_id}/audio/mp3" if row.get("mp3_path") else None,
    }
    return row


@router.get("/capabilities")
def capabilities() -> dict:
    health = breeze_engine.health()
    return {
        **vars(health),
        "modes": ["design", "clone", "direction"],
        "languages": [
            {"id": "en", "name": "English"},
            {"id": "zh", "name": "Chinese"},
        ],
        "english_directions": [
            "General American English",
            "British English",
            "Indian English",
            "Australian English",
            "Canadian English",
            "Irish English",
            "New Zealand English",
            "South African English",
            "Singaporean English",
            "Neutral international English",
        ],
    }


@router.post("/generations", status_code=202)
def create_generation(payload: BreezeGenerationCreate) -> dict:
    health = breeze_engine.health()
    if not health.available:
        raise HTTPException(409, health.reason or "Breeze is unavailable")
    normalized = normalize_text(payload.text)
    phrases = split_phrases(normalized)
    if not phrases:
        raise HTTPException(422, "The script contains no speakable text")
    voice = None
    if payload.voice_id:
        voice = db.fetch_one("SELECT * FROM breeze_voices WHERE id=?", (payload.voice_id,))
        if not voice:
            raise HTTPException(422, "Breeze voice not found")
        if voice["language"] != payload.language:
            raise HTTPException(422, "Voice language does not match the script language")
    if payload.mode in {"clone", "direction"} and (not voice or voice["kind"] != "cloned"):
        raise HTTPException(422, "Clone and Direction modes require a cloned Breeze voice")
    if payload.mode == "design" and not voice and not payload.voice_description.strip():
        raise HTTPException(422, "Describe a voice or select a designed voice")

    generation_id = str(uuid4())
    timestamp = now_iso()
    title = payload.title or speech_text(normalized)[:60].split("\n", 1)[0]
    settings_json = payload.model_dump(
        exclude={
            "text", "title", "mode", "language", "accent_direction", "voice_id",
            "direction", "model_variant",
        }
    )
    # A saved designed voice is a reproducible profile. Its seed and guidance
    # are part of that profile, rather than generic studio defaults.
    if voice and voice["kind"] == "designed":
        settings_json["seed"] = voice["seed"]
        settings_json["cfg_scale"] = voice["cfg_scale"]
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO breeze_generations(id,title,raw_text,normalized_text,mode,language,"
            "accent_direction,voice_id,direction,model_variant,settings_json,status,created_at,"
            "updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,'queued',?,?)",
            (
                generation_id,
                title,
                payload.text,
                normalized,
                payload.mode,
                payload.language,
                payload.accent_direction,
                payload.voice_id,
                payload.direction,
                payload.model_variant,
                json.dumps(settings_json),
                timestamp,
                timestamp,
            ),
        )
        connection.executemany(
            "INSERT INTO breeze_phrases(generation_id,phrase_index,text,source_start,source_end,"
            "pause_after_ms) VALUES (?,?,?,?,?,?)",
            [
                (
                    generation_id,
                    phrase.index,
                    phrase.text,
                    phrase.source_start,
                    phrase.source_end,
                    phrase.pause_after_ms,
                )
                for phrase in phrases
            ],
        )
    breeze_jobs.enqueue(generation_id)
    return generation_detail(generation_id)


@router.get("/generations")
def list_generations(
    q: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
) -> dict:
    where, params = "", []
    if q:
        where = "WHERE title LIKE ? OR raw_text LIKE ? OR direction LIKE ?"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    count = db.fetch_one(
        f"SELECT COUNT(*) AS count FROM breeze_generations {where}", tuple(params)
    )["count"]
    rows = db.fetch_all(
        "SELECT id,title,mode,language,accent_direction,voice_id,direction,model_variant,status,"
        "progress,error,duration,generation_seconds,real_time_factor,created_at,updated_at,wav_path,"
        f"mp3_path FROM breeze_generations {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params + [page_size, (page - 1) * page_size]),
    )
    for row in rows:
        row["audio"] = {
            "wav": f"/api/v2/generations/{row['id']}/audio/wav" if row.pop("wav_path") else None,
            "mp3": f"/api/v2/generations/{row['id']}/audio/mp3" if row.pop("mp3_path") else None,
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
            revision = await asyncio.to_thread(breeze_jobs.wait, generation_id, revision, 15)
            current = generation_detail(generation_id)
            yield f"data: {json.dumps(current)}\n\n"
            if current["status"] in {"complete", "failed", "cancelled"}:
                return

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/generations/{generation_id}/cancel")
def cancel_generation(generation_id: str) -> dict:
    generation_detail(generation_id)
    if not breeze_jobs.cancel(generation_id):
        raise HTTPException(409, "Generation is not currently running")
    return {"ok": True}


@router.post("/generations/{generation_id}/resume", status_code=202)
def resume_generation(generation_id: str) -> dict:
    row = generation_detail(generation_id)
    if row["status"] not in {"interrupted", "failed", "cancelled"}:
        raise HTTPException(409, "Only interrupted, failed, or cancelled jobs can be resumed")
    db.execute(
        "UPDATE breeze_generations SET status='queued',error=NULL,updated_at=? WHERE id=?",
        (now_iso(), generation_id),
    )
    breeze_jobs.enqueue(generation_id)
    return generation_detail(generation_id)


@router.delete("/generations/{generation_id}", status_code=204)
def delete_generation(generation_id: str):
    row = generation_detail(generation_id)
    if row["status"] == "processing":
        raise HTTPException(409, "Cancel the active generation before deleting it")
    db.execute("DELETE FROM breeze_generations WHERE id=?", (generation_id,))
    shutil.rmtree(settings.audio / "breeze" / generation_id, ignore_errors=True)


@router.get("/generations/{generation_id}/audio/{audio_format}")
def generation_audio(generation_id: str, audio_format: str):
    if audio_format not in {"wav", "mp3"}:
        raise HTTPException(404, "Unsupported format")
    row = db.fetch_one(
        "SELECT title,wav_path,mp3_path FROM breeze_generations WHERE id=?", (generation_id,)
    )
    if not row:
        raise HTTPException(404, "Breeze generation not found")
    path = Path(row[f"{audio_format}_path"] or "")
    if not path.is_file():
        raise HTTPException(404, "Audio artifact is missing")
    return FileResponse(
        path,
        media_type="audio/wav" if audio_format == "wav" else "audio/mpeg",
        filename=audio_download_name(row["title"], audio_format),
        content_disposition_type="attachment",
    )


@router.get("/voices")
def list_voices() -> list[dict]:
    return db.fetch_all("SELECT * FROM breeze_voices ORDER BY updated_at DESC")


@router.post("/voices/design", status_code=201)
def create_designed_voice(payload: BreezeDesignedVoiceCreate) -> dict:
    voice_id, timestamp = str(uuid4()), now_iso()
    db.execute(
        "INSERT INTO breeze_voices(id,name,kind,language,accent_direction,description,seed,cfg_scale,"
        "consented,created_at,updated_at) VALUES (?,?,'designed',?,?,?,?,?,1,?,?)",
        (
            voice_id,
            payload.name,
            payload.language,
            payload.accent_direction,
            payload.description,
            payload.seed,
            payload.cfg_scale,
            timestamp,
            timestamp,
        ),
    )
    return db.fetch_one("SELECT * FROM breeze_voices WHERE id=?", (voice_id,))


@router.post("/voices/clone", status_code=201)
def create_cloned_voice(
    name: str = Form(...),
    language: str = Form("en"),
    accent_direction: str = Form(""),
    reference_text: str = Form(...),
    consented: bool = Form(...),
    audio: UploadFile = File(...),
) -> dict:
    if language not in {"en", "zh"}:
        raise HTTPException(422, "Breeze currently supports English and Chinese")
    if not consented:
        raise HTTPException(422, "Voice ownership or permission must be acknowledged")
    if not reference_text.strip():
        raise HTTPException(422, "Enter the exact transcript of the reference audio")
    suffix = Path(audio.filename or "voice.wav").suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a"}:
        raise HTTPException(415, "Use a WAV, MP3, or M4A recording")
    voice_id = str(uuid4())
    folder = settings.voices / "breeze" / voice_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    source = folder / f"original{suffix}"
    with source.open("wb") as output:
        shutil.copyfileobj(audio.file, output)
    processed = folder / "reference.wav"
    try:
        normalize_reference(source, processed)
        seconds = duration(processed)
        if seconds < 3 or seconds > 60:
            raise HTTPException(422, f"Processed recording is {seconds:.1f}s; provide 3–60 seconds")
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    timestamp = now_iso()
    db.execute(
        "INSERT INTO breeze_voices(id,name,kind,language,accent_direction,description,original_path,"
        "processed_path,reference_text,consented,created_at,updated_at) "
        "VALUES (?,?,'cloned',?,?, '',?,?,?,1,?,?)",
        (
            voice_id,
            name,
            language,
            accent_direction,
            str(source),
            str(processed),
            reference_text.strip(),
            timestamp,
            timestamp,
        ),
    )
    return db.fetch_one("SELECT * FROM breeze_voices WHERE id=?", (voice_id,))


@router.post("/voices/{voice_id}/preview")
def preview_voice(voice_id: str, payload: BreezePreviewCreate) -> dict:
    voice = db.fetch_one("SELECT * FROM breeze_voices WHERE id=?", (voice_id,))
    if not voice:
        raise HTTPException(404, "Breeze voice not found")
    folder = settings.voices / "breeze" / voice_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    output = folder / "preview.wav"
    options = {
        "mode": "clone" if voice["kind"] == "cloned" else "design",
        "direction": payload.direction,
        "seed": payload.seed if payload.seed is not None else voice["seed"],
        "cfg_scale": 1.0 if voice["kind"] == "cloned" else voice["cfg_scale"],
    }
    try:
        breeze_engine.synthesize(payload.text, output, voice, options, Event())
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    return {"voice_id": voice_id, "text": payload.text, "audio_url": f"/api/v2/voices/{voice_id}/preview/audio"}


@router.get("/voices/{voice_id}/preview/audio")
def preview_audio(voice_id: str):
    path = settings.voices / "breeze" / voice_id / "preview.wav"
    if not path.is_file():
        raise HTTPException(404, "Generate the Breeze voice preview first")
    return FileResponse(path, media_type="audio/wav", filename=f"{voice_id}-preview.wav")


@router.delete("/voices/{voice_id}", status_code=204)
def delete_voice(voice_id: str):
    row = db.fetch_one("SELECT * FROM breeze_voices WHERE id=?", (voice_id,))
    if not row:
        raise HTTPException(404, "Breeze voice not found")
    db.execute("DELETE FROM breeze_voices WHERE id=?", (voice_id,))
    shutil.rmtree(settings.voices / "breeze" / voice_id, ignore_errors=True)
