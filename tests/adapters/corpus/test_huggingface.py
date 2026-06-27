"""Découverte HuggingFace : filtre référence, parsing API, repli best-effort."""

from __future__ import annotations

import pytest

from cinoc.adapters.corpus import huggingface
from cinoc.adapters.corpus._http import HttpFetchError
from cinoc.adapters.corpus.huggingface import (
    CURATED_DATASET_TAG,
    HuggingFaceCatalogue,
    _parse_api,
    _parse_curated,
    discover_curated,
    search_reference,
)


def test_search_reference_filters() -> None:
    assert {d.dataset_id for d in search_reference("norhand")} == {"Teklia/NorHand"}
    assert all(d.source == "reference" for d in search_reference())
    assert len(search_reference(language="fr")) >= 1
    assert search_reference("zzz-introuvable") == ()


def test_parse_api_maps_and_skips_invalid() -> None:
    payload = [
        {"id": "user/ds1", "downloads": 42},
        {"downloads": 1},  # pas d'id → ignoré
        "garbage",  # pas un dict → ignoré
        {"id": "user/ds2"},  # downloads absent → 0
    ]
    out = _parse_api(payload)
    assert [d.dataset_id for d in out] == ["user/ds1", "user/ds2"]
    assert out[0].downloads == 42 and out[0].source == "api"
    assert out[1].downloads == 0


def test_parse_api_non_list_is_empty() -> None:
    assert _parse_api({"results": []}) == ()


def test_search_api_failure_returns_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, **kwargs: object) -> object:
        raise HttpFetchError("API down")

    monkeypatch.setattr(huggingface, "fetch_json", boom)
    results = HuggingFaceCatalogue().search("", include_api=True)
    assert results  # jamais bloqué
    assert all(d.source == "reference" for d in results)


def test_search_api_dedups_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    # L'API renvoie un id déjà en référence + un nouveau → pas de doublon.
    def fake(url: str, **kwargs: object) -> object:
        return [{"id": "Teklia/NorHand"}, {"id": "new/dataset"}]

    monkeypatch.setattr(huggingface, "fetch_json", fake)
    ids = [d.dataset_id for d in HuggingFaceCatalogue().search("")]
    assert ids.count("Teklia/NorHand") == 1
    assert "new/dataset" in ids


# --- Découverte des datasets curés (par compte + tag de convention) -----------


def test_parse_curated_maps_and_pins_revision() -> None:
    payload = [
        {
            "id": "me/Cinoc-Dresden",
            "sha": "abc123def456",
            "lastModified": "2026-06-01T12:00:00Z",
            "tags": ["iiif", CURATED_DATASET_TAG],
        },
    ]
    out = _parse_curated(payload, tag=CURATED_DATASET_TAG)
    assert len(out) == 1
    assert out[0].repo_id == "me/Cinoc-Dresden"
    assert out[0].revision == "abc123def456"  # SHA épinglé pour la repro
    assert out[0].last_modified == "2026-06-01T12:00:00Z"


def test_parse_curated_filters_untagged_and_invalid() -> None:
    payload = [
        {"id": "me/tagged", "tags": [CURATED_DATASET_TAG]},
        {"id": "me/other", "tags": ["ocr"]},  # pas le tag → écarté
        {"tags": [CURATED_DATASET_TAG]},  # pas d'id → écarté
        "garbage",  # pas un dict → écarté
        {"id": "me/no-sha", "tags": [CURATED_DATASET_TAG]},  # sans sha → revision None
    ]
    out = _parse_curated(payload, tag=CURATED_DATASET_TAG)
    assert [d.repo_id for d in out] == ["me/tagged", "me/no-sha"]
    assert out[1].revision is None


def test_discover_curated_queries_author_and_tag() -> None:
    seen: dict[str, str] = {}

    def fake(url: str) -> object:
        seen["url"] = url
        return [{"id": "me/ds", "tags": [CURATED_DATASET_TAG], "sha": "ff"}]

    out = discover_curated("me", fetcher=fake)
    assert [d.repo_id for d in out] == ["me/ds"]
    assert "author=me" in seen["url"]
    assert f"filter={CURATED_DATASET_TAG}" in seen["url"]


def test_discover_curated_empty_author_skips_network() -> None:
    def boom(url: str) -> object:
        raise AssertionError("aucun appel réseau attendu sans compte")

    assert discover_curated("", fetcher=boom) == ()


def test_discover_curated_api_failure_is_best_effort() -> None:
    def boom(url: str) -> object:
        raise HttpFetchError("API down")

    assert discover_curated("me", fetcher=boom) == ()
