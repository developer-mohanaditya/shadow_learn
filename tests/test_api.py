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


def test_breeze_capabilities_and_designed_voice():
    with TestClient(app) as client:
        capabilities = client.get("/api/v2/capabilities")
        assert capabilities.status_code == 200
        assert capabilities.json()["modes"] == ["design", "clone", "direction"]
        assert {item["id"] for item in capabilities.json()["languages"]} == {"en", "zh"}
        created = client.post(
            "/api/v2/voices/design",
            json={
                "name": "Clear coach",
                "language": "en",
                "accent_direction": "Indian English",
                "description": "A warm, clear adult voice with measured pacing.",
            },
        )
        assert created.status_code == 201
        assert created.json()["kind"] == "designed"
        voices = client.get("/api/v2/voices")
        assert any(item["name"] == "Clear coach" for item in voices.json())


def test_audio_download_name_is_portable():
    assert audio_download_name("My First Practice: Hello, World!", "mp3") == (
        "my-first-practice-hello-world.mp3"
    )
    assert audio_download_name("Prôféshare AI", "mp3") == "profeshare-ai.mp3"
    assert audio_download_name("你好", "wav") == "shadowlearn-audio.wav"
