"""Aide au composeur côté HTTP : aperçu de normalisation + modèles (live).

Les listes de lecture (état des moteurs, profils de métriques/normalisation) sont
rendues côté serveur et leur logique est couverte par ``tests/app/test_engines``
+ ``test_run_planning`` — pas d'API JSON dédiée.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cinoc.interfaces.web.app import create_app


def _client(tmp_path: Path, *, public_mode: bool = False) -> TestClient:
    return TestClient(
        create_app(reports_dir=tmp_path, rate_limit=1000, public_mode=public_mode)
    )


def test_models_endpoint_lists_provider_models_with_vision(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/api/models/openai").json()
    assert body["provider"] == "openai"
    names = {m["name"]: m["vision"] for m in body["models"]}
    assert "gpt-4o" in names and names["gpt-4o"] is True


def test_models_endpoint_unknown_provider_is_empty(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/api/models/bogus").json()
    assert body == {"provider": "bogus", "models": []}  # champ libre, pas d'erreur


def test_normalization_preview_named_and_custom(tmp_path: Path) -> None:
    from cinoc.interfaces.web.security.csrf import CSRF_HEADER

    client = _client(tmp_path)
    headers = {CSRF_HEADER: "1"}
    # profil nommé : caseless → minuscules.
    r = client.post(
        "/api/normalization/preview",
        headers=headers,
        json={"sample": "NOSTRE", "profile": "caseless"},
    )
    assert r.status_code == 200 and r.json()["normalized"] == "nostre"
    # config YAML custom (sans persistance) : exclut « X ».
    r = client.post(
        "/api/normalization/preview",
        headers=headers,
        json={"sample": "aXb", "config": 'exclude_chars: "X"'},
    )
    assert r.json()["normalized"] == "ab"


def test_normalization_preview_invalid_config_is_422(tmp_path: Path) -> None:
    from cinoc.interfaces.web.security.csrf import CSRF_HEADER

    r = _client(tmp_path).post(
        "/api/normalization/preview",
        headers={CSRF_HEADER: "1"},
        json={"sample": "x", "config": "bogus_key: 1"},
    )
    assert r.status_code == 422


def test_normalization_preview_requires_csrf(tmp_path: Path) -> None:
    r = _client(tmp_path).post(
        "/api/normalization/preview", json={"sample": "x", "profile": "nfc"}
    )
    assert r.status_code == 403
