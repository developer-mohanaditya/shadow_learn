from fastapi.testclient import TestClient

from shadowlearn.api import audio_download_name
from shadowlearn.main import app


def test_health_and_preset_voices():
    with TestClient(app) as client:
        health = client.get("/api/system/health")
        assert health.status_code == 200
        assert health.json()["database"] == "ok"
        voices = client.get("/api/voices")
        assert voices.status_code == 200
        assert any(item["engine"] == "kokoro" for item in voices.json())
        assert any(item["engine"] == "zonos2" for item in voices.json())


def test_empty_generation_is_rejected():
    with TestClient(app) as client:
        response = client.post("/api/generations", json={"text": ""})
        assert response.status_code == 422


def test_audio_download_name_is_portable():
    assert audio_download_name("My First Practice: Hello, World!", "mp3") == (
        "my-first-practice-hello-world.mp3"
    )
    assert audio_download_name("Prôféshare AI", "mp3") == "profeshare-ai.mp3"
    assert audio_download_name("你好", "wav") == "shadowlearn-audio.wav"
