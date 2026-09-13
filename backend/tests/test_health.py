from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_is_available_without_any_device() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_docs_are_namespaced() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/docs")
    assert response.status_code == 200
