from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import settings
from .database import db
from .jobs import jobs


def backup_scheduler(stop: threading.Event) -> None:
    while not stop.wait(3600):
        latest = db.fetch_one("SELECT created_at FROM backups ORDER BY created_at DESC LIMIT 1")
        if not latest or time.time() - datetime.fromisoformat(latest["created_at"]).timestamp() > 86400:
            db.create_backup(kind="daily")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.initialize()
    jobs.start()
    stop = threading.Event()
    scheduler = threading.Thread(target=backup_scheduler, args=(stop,), daemon=True)
    scheduler.start()
    yield
    stop.set()
    jobs.stop()


app = FastAPI(title="Shadow Learn", version="0.1.0", lifespan=lifespan)
app.include_router(router)

assets = settings.frontend_dist / "assets"
if assets.is_dir():
    app.mount("/assets", StaticFiles(directory=assets), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    candidate = settings.frontend_dist / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    index = settings.frontend_dist / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"message": "Shadow Learn API is running. Build the frontend with npm run build."}


def run() -> None:
    uvicorn.run("shadowlearn.main:app", host="127.0.0.1", port=8420, reload=False)


if __name__ == "__main__":
    run()
