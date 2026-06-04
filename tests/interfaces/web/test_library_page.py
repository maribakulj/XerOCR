"""Page « Bibliothèque » (S6 découverte) : rendu serveur, catalogues mockés."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from xerocr.adapters.corpus.htr_united import HTRUnitedCatalogue, HTRUnitedEntry
from xerocr.adapters.corpus.huggingface import HuggingFaceDataset
from xerocr.adapters.storage.history_store import HistoryStore
from xerocr.interfaces.web.app import _TEMPLATES_DIR, create_app
from xerocr.interfaces.web.routers.home import build_home_router

_HTR_REMOTE = HTRUnitedCatalogue(
    entries=(
        HTRUnitedEntry(
            id="cremma-medieval",
            title="CREMMA Medieval",
            url="https://github.com/HTR-United/cremma-medieval",
            description="Manuscrits médiévaux",
            languages=("fr", "la"),
        ),
    ),
    source="remote",
)
_HF = (
    HuggingFaceDataset(
        dataset_id="Teklia/NorHand",
        title="NorHand",
        description="",
        languages=("no",),
        downloads=1200,
        source="reference",
    ),
)


class _FakeHF:
    last_query: str | None = None

    def search(self, q: str = "", language: str | None = None, **_: object):
        _FakeHF.last_query = q
        return _HF


def _client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    catalogue: HTRUnitedCatalogue = _HTR_REMOTE,
) -> TestClient:
    monkeypatch.setattr(
        "xerocr.interfaces.web.routers.home.fetch_catalogue", lambda: catalogue
    )
    monkeypatch.setattr(
        "xerocr.interfaces.web.routers.home.HuggingFaceCatalogue", _FakeHF
    )
    templates = Jinja2Templates(directory=_TEMPLATES_DIR)
    app = FastAPI()
    app.include_router(
        build_home_router(
            tmp_path / "reports",
            templates,
            statuses=lambda: (),
            history_store=HistoryStore(tmp_path / "h.db"),
        )
    )
    return TestClient(app)


def test_library_caches_catalogue_across_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # F1 : deux chargements de /library ne refetchent pas le catalogue HTR-United
    # (cache TTL partagé par le routeur). Compteur sur fetch_catalogue.
    calls = {"n": 0}

    def counting_fetch() -> HTRUnitedCatalogue:
        calls["n"] += 1
        return _HTR_REMOTE

    monkeypatch.setattr(
        "xerocr.interfaces.web.routers.home.fetch_catalogue", counting_fetch
    )
    monkeypatch.setattr(
        "xerocr.interfaces.web.routers.home.HuggingFaceCatalogue", _FakeHF
    )
    templates = Jinja2Templates(directory=_TEMPLATES_DIR)
    app = FastAPI()
    app.include_router(
        build_home_router(
            tmp_path / "reports",
            templates,
            statuses=lambda: (),
            history_store=HistoryStore(tmp_path / "h.db"),
        )
    )
    client = TestClient(app)
    assert client.get("/library").status_code == 200
    assert client.get("/library").status_code == 200
    assert calls["n"] == 1  # un seul fetch réseau pour deux chargements


def test_library_lists_both_catalogues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _client(tmp_path, monkeypatch).get("/library").text
    assert "CREMMA Medieval" in body  # HTR-United
    assert "Teklia/NorHand" in body  # HuggingFace


def test_library_demo_badge_when_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    demo = _client(tmp_path, monkeypatch, catalogue=HTRUnitedCatalogue.from_demo())
    assert "démonstration" in demo.get("/library").text
    # catalogue distant → pas de badge démo
    assert "démonstration" not in _client(tmp_path, monkeypatch).get("/library").text


def test_library_search_passes_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _FakeHF.last_query = None
    body = _client(tmp_path, monkeypatch).get("/library?q=latin").text
    assert _FakeHF.last_query == "latin"  # la requête atteint la recherche HF
    assert 'value="latin"' in body  # et est réaffichée dans le formulaire


def test_library_server_rendered_active_nav(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _client(tmp_path, monkeypatch).get("/library").text
    assert "<script" not in body
    assert 'aria-current="page"' in body


def test_library_english(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    body = _client(tmp_path, monkeypatch).get("/library?lang=en").text
    assert "Library" in body and "Search" in body


def test_library_is_live_nav_link_from_home(tmp_path: Path) -> None:
    # L'accueil ne fait aucun appel réseau ; le lien Bibliothèque est vivant.
    client = TestClient(
        create_app(
            reports_dir=tmp_path / "r",
            uploads_dir=tmp_path / "u",
            rate_limit=1000,
        )
    )
    assert 'href="/library?lang=fr"' in client.get("/").text
