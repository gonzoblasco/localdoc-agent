from fastapi.testclient import TestClient

from agent.ui import app

client = TestClient(app)


def test_index_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert "Nido" in r.text


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "ollama_ok" in data
    assert "documents" in data
    assert "chunks" in data


def test_delete_ok():
    r = client.post("/delete")
    assert r.status_code == 204
