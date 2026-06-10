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


def test_normalization_profiles_are_read_dynamically(tmp_path: Path) -> None:
    from xerocr.formats.text.normalization import NORMALIZATION_PROFILES

    body = _client(tmp_path).get("/api/normalization/profiles").json()
    # Jamais une liste statique : l'endpoint reflète la couche 2 telle quelle.
    assert body["profiles"] == sorted(NORMALIZATION_PROFILES)
    assert "nfc" in body["profiles"]
