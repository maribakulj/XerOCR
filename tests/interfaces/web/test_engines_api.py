"""Onglet « Moteurs » côté HTTP : ``GET /api/engines`` (read-only)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app


def _client(tmp_path: Path, *, public_mode: bool = False) -> TestClient:
    return TestClient(
        create_app(reports_dir=tmp_path, rate_limit=1000, public_mode=public_mode)
    )


def test_lists_all_socle_engines(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/api/engines").json()
    kinds = {e["kind"] for e in body["engines"]}
    assert kinds == {
        "precomputed", "tesseract", "kraken", "pero", "calamari", "mistral_ocr",
        "google_vision", "azure_di", "openai", "anthropic", "mistral", "ollama",
    }
    # forme du contrat : chaque entrée porte available + detail
    for entry in body["engines"]:
        assert isinstance(entry["available"], bool)
        assert entry["detail"]


def test_precomputed_is_available(tmp_path: Path) -> None:
    engines = _client(tmp_path).get("/api/engines").json()["engines"]
    pre = next(e for e in engines if e["kind"] == "precomputed")
    assert pre["available"] is True


def test_cloud_unavailable_reason_is_key_not_mode(tmp_path: Path) -> None:
    # Plus de masquage « mode public » : openai est indisponible faute de clé
    # (et/ou de SDK), pas à cause du mode. Le motif n'est plus « public ».
    engines = _client(tmp_path, public_mode=True).get("/api/engines").json()["engines"]
    openai = next(e for e in engines if e["kind"] == "openai")
    assert openai["available"] is False
    assert "public" not in openai["detail"]


def test_metric_profiles_endpoint_lists_standard_first(tmp_path: Path) -> None:
    # Source unique pour le sélecteur du lanceur (read-only, pas de CSRF).
    body = _client(tmp_path).get("/api/metric-profiles").json()
    profiles = body["profiles"]
    assert profiles[0]["name"] == "standard"  # défaut historique d'abord
    names = {p["name"] for p in profiles}
    assert {"standard", "essentiel", "philologie"} <= names
    # chaque entrée porte la liste ordonnée de ses métriques (libellé self-doc)
    standard = next(p for p in profiles if p["name"] == "standard")
    assert standard["metrics"][0] == "cer"


def test_normalization_profiles_are_read_dynamically(tmp_path: Path) -> None:
    from xerocr.formats.text.normalization import NORMALIZATION_PROFILES

    body = _client(tmp_path).get("/api/normalization/profiles").json()
    # Jamais une liste statique : l'endpoint reflète la couche 2 telle quelle.
    assert body["profiles"] == sorted(NORMALIZATION_PROFILES)
    assert "nfc" in body["profiles"]


def test_models_endpoint_lists_provider_models_with_vision(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/api/models/openai").json()
    assert body["provider"] == "openai"
    names = {m["name"]: m["vision"] for m in body["models"]}
    assert "gpt-4o" in names and names["gpt-4o"] is True


def test_models_endpoint_unknown_provider_is_empty(tmp_path: Path) -> None:
    body = _client(tmp_path).get("/api/models/bogus").json()
    assert body == {"provider": "bogus", "models": []}  # champ libre, pas d'erreur


def test_normalization_preview_named_and_custom(tmp_path: Path) -> None:
    from xerocr.interfaces.web.security.csrf import CSRF_HEADER

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
    from xerocr.interfaces.web.security.csrf import CSRF_HEADER

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
