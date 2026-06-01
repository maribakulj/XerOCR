"""``create_app()`` : factory (instances neuves) + route santé, via TestClient."""

from __future__ import annotations

from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import API_VERSION, create_app


def test_create_app_is_a_factory() -> None:
    # factory, pas un singleton de module : deux appels → deux instances.
    assert create_app() is not create_app()


def test_app_metadata() -> None:
    app = create_app()
    assert app.title == "XerOCR"
    assert app.version == API_VERSION


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
