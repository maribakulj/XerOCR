"""Découverte HuggingFace : filtre référence, parsing API, repli best-effort."""

from __future__ import annotations

import pytest

from xerocr.adapters.corpus import huggingface
from xerocr.adapters.corpus._http import HttpFetchError
from xerocr.adapters.corpus.huggingface import (
    HuggingFaceCatalogue,
    _parse_api,
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
