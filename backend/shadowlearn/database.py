from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from .config import settings


MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS voices (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            engine TEXT NOT NULL,
            accent TEXT NOT NULL DEFAULT 'us',
            kind TEXT NOT NULL CHECK(kind IN ('preset','cloned')),
            original_path TEXT,
            processed_path TEXT,
            embedding_path TEXT,
            consented INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS generations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            engine TEXT NOT NULL,
            voice_id TEXT,
            settings_json TEXT NOT NULL,
            status TEXT NOT NULL,
            progress REAL NOT NULL DEFAULT 0,
            error TEXT,
            wav_path TEXT,
            mp3_path TEXT,
            duration REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(voice_id) REFERENCES voices(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS generations_created_at ON generations(created_at DESC);
        CREATE TABLE IF NOT EXISTS phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_id TEXT NOT NULL,
            phrase_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            source_start INTEGER NOT NULL,
            source_end INTEGER NOT NULL,
            pause_after_ms INTEGER NOT NULL DEFAULT 0,
            start_time REAL,
            end_time REAL,
            artifact_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            UNIQUE(generation_id, phrase_index),
            FOREIGN KEY(generation_id) REFERENCES generations(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS backups (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            integrity_ok INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            id TEXT PRIMARY KEY,
            engine TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            score REAL,
            qualifies INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """,
    )
]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path = settings.database):
        self.path = path
        self._write_lock = threading.RLock()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._write_lock, self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def initialize(self) -> None:
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                row["version"] for row in connection.execute("SELECT version FROM schema_migrations")
            }
        for version, sql in MIGRATIONS:
            if version in applied:
                continue
            if self.path.exists() and self.path.stat().st_size:
                self.create_backup(kind=f"pre-migration-{version}", register=False)
            with self.transaction() as connection:
                connection.executescript(sql)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, now_iso()),
                )
        self.mark_interrupted()
        self.seed_presets()

    def mark_interrupted(self) -> None:
        with self.transaction() as connection:
            connection.execute(
                "UPDATE generations SET status='interrupted', error='Application stopped during generation', updated_at=? WHERE status IN ('queued','processing')",
                (now_iso(),),
            )

    def seed_presets(self) -> None:
        kokoro_voices = {
            "us": (
                "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
                "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
                "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
                "am_onyx", "am_puck", "am_santa",
            ),
            "uk": (
                "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
                "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
            ),
        }
        presets = [
            (
                f"kokoro-{voice.replace('_', '-')}",
                voice.split("_", 1)[1].replace("_", " ").title(),
                "kokoro",
                accent,
            )
            for accent, voices in kokoro_voices.items()
            for voice in voices
        ]
        presets.extend([
            ("zonos2-american-female", "American Female", "zonos2", "us"),
            ("zonos2-american-male", "American Male", "zonos2", "us"),
            ("zonos2-british-female", "British Female", "zonos2", "uk"),
        ])
        presets.extend(self._system_english_presets())
        timestamp = now_iso()
        with self.transaction() as connection:
            for voice_id, name, engine, accent in presets:
                connection.execute(
                    "INSERT OR IGNORE INTO voices(id,name,engine,accent,kind,consented,created_at,updated_at) VALUES (?,?,?,?, 'preset',1,?,?)",
                    (voice_id, name, engine, accent, timestamp, timestamp),
                )

    @staticmethod
    def _system_english_presets() -> list[tuple[str, str, str, str]]:
        if not shutil.which("say"):
            return []
        try:
            output = subprocess.run(
                ["/usr/bin/say", "-v", "?"], check=True, capture_output=True, text=True
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            return []
        accent_by_locale = {
            "en_US": "us", "en_GB": "uk", "en_IN": "in",
            "en_AU": "au", "en_IE": "ie", "en_ZA": "za",
        }
        result = []
        for line in output.splitlines():
            match = re.match(r"^(.+?)\s{2,}(en_[A-Z]{2})\s+#", line)
            if not match:
                continue
            name, locale = match.groups()
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            result.append(
                (f"system-{slug}", f"{name} (macOS)", "system", accent_by_locale.get(locale, "us"))
            )
        return result

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, params).fetchall()]

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(sql, params).fetchone()
            return dict(row) if row else None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self.transaction() as connection:
            connection.execute(sql, params)

    def create_backup(self, kind: str = "manual", register: bool = True) -> dict[str, Any]:
        from uuid import uuid4

        backup_id = str(uuid4())
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        target = settings.backups / f"shadowing-{timestamp}-{backup_id[:8]}.db"
        with self._write_lock, self.connect() as source, sqlite3.connect(target) as destination:
            source.backup(destination)
        with sqlite3.connect(target) as check:
            integrity_ok = check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        record = {
            "id": backup_id,
            "path": str(target),
            "kind": kind,
            "size_bytes": target.stat().st_size,
            "integrity_ok": integrity_ok,
            "created_at": now_iso(),
        }
        if register:
            self.execute(
                "INSERT INTO backups(id,path,kind,size_bytes,integrity_ok,created_at) VALUES (?,?,?,?,?,?)",
                (
                    record["id"], record["path"], record["kind"], record["size_bytes"],
                    int(record["integrity_ok"]), record["created_at"],
                ),
            )
            self.prune_backups()
        return record

    def prune_backups(self) -> None:
        backups = self.fetch_all("SELECT * FROM backups ORDER BY created_at DESC")
        keep = {row["id"] for row in backups[:7]}
        weekly_seen: set[str] = set()
        for row in backups[7:]:
            try:
                week = datetime.fromisoformat(row["created_at"]).strftime("%G-%V")
            except ValueError:
                continue
            if len(weekly_seen) < 4 and week not in weekly_seen:
                weekly_seen.add(week)
                keep.add(row["id"])
        for row in backups:
            if row["id"] in keep:
                continue
            Path(row["path"]).unlink(missing_ok=True)
            self.execute("DELETE FROM backups WHERE id=?", (row["id"],))

    def restore_backup(self, backup_id: str) -> None:
        record = self.fetch_one("SELECT * FROM backups WHERE id=?", (backup_id,))
        if not record:
            raise ValueError("Backup not found")
        source = Path(record["path"])
        with sqlite3.connect(source) as check:
            if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup failed integrity validation")
        safety = self.create_backup(kind="pre-restore", register=False)
        try:
            with sqlite3.connect(source) as backup, self.connect() as destination:
                backup.backup(destination)
            with self.connect() as check:
                if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Restored database failed integrity validation")
        except Exception:
            with sqlite3.connect(safety["path"]) as backup, self.connect() as destination:
                backup.backup(destination)
            raise


db = Database()


def decode_json_fields(record: dict[str, Any]) -> dict[str, Any]:
    for key in ("settings_json", "metrics_json"):
        if key in record and isinstance(record[key], str):
            record[key.removesuffix("_json")] = json.loads(record.pop(key))
    return record
