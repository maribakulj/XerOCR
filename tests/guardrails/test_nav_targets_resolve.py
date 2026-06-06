"""Garde-fou : tout lien de navigation **vivant** répond, même hors-ligne.

La barre de navigation annonce un ensemble de vues « vivantes »
(``home._LIVE_VIEWS``). Chacune doit répondre sans 500 dans des conditions
réalistes de Space (réseau sortant indisponible) : un lien annoncé qui mène à
une *Internal Server Error* est une incohérence d'UI. Ce test itère
**programmatiquement** sur ``_LIVE_VIEWS`` → il attrape aussi tout futur lien
ajouté sans route fonctionnelle.

Verrou de non-régression : toutes les vues vivantes répondent hors-ligne (le
repli des catalogues couvre ``/library``) ; le test échoue si un lien annoncé
se remet à renvoyer 500.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.adapters.corpus import _http
from xerocr.adapters.corpus._http import SsrfError
from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.routers.home import _LIVE_VIEWS


def _raise_ssrf(url: str) -> tuple[str, ...]:
    raise SsrfError("réseau sortant indisponible (simulé)")


def test_all_live_nav_targets_resolve_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_http, "assert_public_url", _raise_ssrf)
    client = TestClient(
        create_app(
            reports_dir=tmp_path / "reports",
            uploads_dir=tmp_path / "uploads",
            rate_limit=10_000,
        ),
        raise_server_exceptions=False,
    )
    broken = {
        path: client.get(path).status_code
        for path in sorted(set(_LIVE_VIEWS.values()))
    }
    offenders = {path: code for path, code in broken.items() if code >= 500}
    assert not offenders, f"liens de navigation en erreur serveur : {offenders}"
