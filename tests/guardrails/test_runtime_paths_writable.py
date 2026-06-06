"""Garde-fou : l'écriture runtime ne se fait pas dans le dossier rapports baké.

Sur un Space, le dossier des rapports est **livré dans l'image** (``COPY``,
appartenant à root) et l'app tourne en utilisateur non-root : il est donc
**non inscriptible**. La base d'historique (et plus largement tout état runtime)
ne doit pas y être écrite — sinon ``/history`` et l'enregistrement des runs
échouent. Picarones écrivait dans ``~/.picarones/`` (inscriptible) ; XerOCR doit
résoudre un emplacement de données **distinct** du dossier rapports.

On fixe ``XEROCR_DATA_DIR`` (compat avant : ignoré aujourd'hui) et on vérifie
qu'aucun ``history.db`` n'apparaît dans le dossier rapports après un appel à
``/history``. ``xfail(strict)`` jusqu'à la séparation des deux emplacements.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app


@pytest.mark.xfail(
    strict=True,
    reason="la base d'historique ne doit pas être écrite dans le dossier "
    "rapports (non inscriptible sur un Space).",
)
def test_history_db_is_not_written_into_reports_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reports_dir = tmp_path / "reports_baked"
    reports_dir.mkdir()
    # Emplacement de données séparé attendu après correction (ignoré avant).
    monkeypatch.setenv("XEROCR_DATA_DIR", str(tmp_path / "data"))

    client = TestClient(
        create_app(
            reports_dir=reports_dir,
            uploads_dir=tmp_path / "uploads",
            rate_limit=10_000,
        )
    )
    assert client.get("/history").status_code == 200
    assert not (reports_dir / "history.db").exists(), (
        "history.db écrit dans le dossier rapports baké (read-only sur Space)"
    )
