"""Garde-fou : les pages ne renvoient pas **500** quand une source échoue.

Les tests de page existants couvrent le chemin heureux (dossier inscriptible,
réseau présent) ; ils n'attrapent donc pas les *Internal Server Error* observés
sur Hugging Face :

- ``/library`` appelle des catalogues distants. Si la résolution réseau échoue
  (``SsrfError`` levée par ``assert_public_url`` sur échec DNS, ou timeout),
  le repli « démo/référence » doit s'enclencher → page **dégradée**, pas 500.
- ``/history`` lit un store SQLite. Si l'ouverture échoue
  (``sqlite3.OperationalError`` : dossier non inscriptible sur le Space), la
  page doit se dégrader, pas renvoyer 500.

On injecte la panne **au bon joint** (le réseau / le store), pas en remplaçant
le repli — ainsi le test passe au vert exactement quand le repli est réparé.
``raise_server_exceptions=False`` pour observer le code HTTP au lieu de propager.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.adapters.corpus import _http
from xerocr.adapters.corpus._http import SsrfError
from xerocr.adapters.storage.history_store import HistoryRecord, HistoryStore
from xerocr.interfaces.web.app import create_app


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        reports_dir=tmp_path / "reports",
        uploads_dir=tmp_path / "uploads",
        rate_limit=10_000,
    )
    return TestClient(app, raise_server_exceptions=False)


def _raise_ssrf(url: str) -> tuple[str, ...]:
    raise SsrfError("résolution DNS impossible (simulée)")


def _raise_sqlite(
    self: HistoryStore, *, limit: int = 1000
) -> tuple[HistoryRecord, ...]:
    raise sqlite3.OperationalError("unable to open database file")


def test_library_degrades_when_network_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Réseau coupé au plus bas niveau : tout fetch de catalogue lève SsrfError.
    monkeypatch.setattr(_http, "assert_public_url", _raise_ssrf)
    resp = _client(tmp_path).get("/library")
    assert resp.status_code == 200


def test_history_degrades_when_store_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Le store ne peut pas ouvrir sa base (cas Space : dossier non inscriptible).
    monkeypatch.setattr(HistoryStore, "all_records", _raise_sqlite)
    resp = _client(tmp_path).get("/history")
    assert resp.status_code == 200
