"""Catalogue HTR-United : parsing YAML, recherche, repli démo (sans réseau)."""

from __future__ import annotations

import pytest

from xerocr.adapters.corpus import htr_united
from xerocr.adapters.corpus._http import HttpFetchError
from xerocr.adapters.corpus.htr_united import (
    HTRUnitedCatalogue,
    fetch_catalogue,
    parse_catalogue,
)

_YAML = """
- title: Corpus A
  url: https://github.com/HTR-United/corpus-a
  description: Manuscrits A
  language: [fr, la]
- title: Corpus B
  url: https://github.com/HTR-United/corpus-b
  language:
    - iso: de
"""


def test_parse_catalogue_list_and_language_forms() -> None:
    entries = parse_catalogue(_YAML)
    assert [e.id for e in entries] == ["corpus-a", "corpus-b"]
    assert entries[0].languages == ("fr", "la")
    assert entries[1].languages == ("de",)  # forme dict {iso: …}


def test_parse_catalogue_tolerates_garbage() -> None:
    assert parse_catalogue("just a string") == ()
    assert parse_catalogue("") == ()


def test_search_query_and_language() -> None:
    cat = HTRUnitedCatalogue(entries=parse_catalogue(_YAML), source="remote")
    assert {e.id for e in cat.search("manuscrits")} == {"corpus-a"}
    assert {e.id for e in cat.search(language="de")} == {"corpus-b"}
    assert len(cat.search()) == 2


def test_from_demo_is_flagged() -> None:
    cat = HTRUnitedCatalogue.from_demo()
    assert cat.is_demo and cat.source == "demo"
    assert len(cat.entries) >= 1


def test_fetch_catalogue_falls_back_to_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, **kwargs: object) -> str:
        raise HttpFetchError("réseau coupé")

    monkeypatch.setattr(htr_united, "fetch_text", boom)
    cat = fetch_catalogue()
    assert cat.is_demo  # repli silencieux, jamais d'exception remontée
