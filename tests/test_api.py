from fastapi.testclient import TestClient

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
