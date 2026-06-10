"""Lanceur web : CSRF d'abord, démo, puis concurrents (gardes HTTP), mode public."""

from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.app.engines import engine_statuses
from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.security.csrf import CSRF_HEADER

_CSRF = {CSRF_HEADER: "1"}


def _client(tmp_path: Path, *, public_mode: bool = False) -> TestClient:
    return TestClient(
        create_app(reports_dir=tmp_path, rate_limit=1000, public_mode=public_mode)
    )


def _poll_until_terminal(
    client: TestClient, job_id: str, timeout: float = 30.0
) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/runs/{job_id}").json()
        if body["state"] in {"done", "failed", "cancelled"}:
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} non terminé dans le délai")


# --- Sécurité d'abord (CSRF) -------------------------------------------------


def test_post_without_csrf_is_403(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/runs")
    assert resp.status_code == 403
    assert _client(tmp_path).get("/api/reports").json() == {"reports": []}


def test_cancel_without_csrf_is_403(tmp_path: Path) -> None:
    assert _client(tmp_path).post("/api/runs/whatever/cancel").status_code == 403


def test_csrf_header_allows_post(tmp_path: Path) -> None:
    # Sans corps → démonstration → 201.
    resp = _client(tmp_path).post("/api/runs", headers=_CSRF)
    assert resp.status_code == 201
    assert "job_id" in resp.json()


# --- Bout-en-bout démo : lancer → exécuter → résultat visible ----------------


def test_launch_runs_and_result_appears(tmp_path: Path) -> None:
    client = _client(tmp_path)
    job_id = client.post("/api/runs", headers=_CSRF).json()["job_id"]
    job = _poll_until_terminal(client, job_id)
    assert job["state"] == "done"
    name = job["report_name"]
    assert name in client.get("/api/reports").json()["reports"]
    assert client.get(f"/reports/{name}").status_code == 200


def test_status_unknown_job_is_404(tmp_path: Path) -> None:
    assert _client(tmp_path).get("/api/runs/absent").status_code == 404


def test_cancel_unknown_job_is_404(tmp_path: Path) -> None:
    resp = _client(tmp_path).post("/api/runs/absent/cancel", headers=_CSRF)
    assert resp.status_code == 404


def test_public_mode_allows_local_demo(tmp_path: Path) -> None:
    client = _client(tmp_path, public_mode=True)
    resp = client.post("/api/runs", headers=_CSRF)
    assert resp.status_code == 201
    assert _poll_until_terminal(client, resp.json()["job_id"])["state"] == "done"


# --- Concurrents : sélection + gardes HTTP -----------------------------------

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _post(client: TestClient, body: dict) -> object:
    return client.post("/api/runs", headers=_CSRF, json=body)


def _upload_demo_corpus(client: TestClient) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.png", _PNG)
        zf.writestr("a.gt.txt", b"verite")
    files = {"file": ("c.zip", buf.getvalue(), "application/zip")}
    return client.post("/api/corpus", files=files, headers=_CSRF).json()["corpus_id"]


def test_unknown_engine_is_422(tmp_path: Path) -> None:
    resp = _post(_client(tmp_path), {"competitors": [{"engine": "bogus"}]})
    assert resp.status_code == 422


def test_extra_field_on_request_is_422(tmp_path: Path) -> None:
    assert _post(_client(tmp_path), {"competitors": [], "x": 1}).status_code == 422


def test_extra_field_on_competitor_is_422(tmp_path: Path) -> None:
    resp = _post(_client(tmp_path), {"competitors": [{"engine": "tesseract", "x": 1}]})
    assert resp.status_code == 422


def test_invalid_mode_is_422(tmp_path: Path) -> None:
    # mode hors Literal → rejet net par Pydantic.
    body = {"competitors": [{"engine": "tesseract", "mode": "bogus"}]}
    assert _post(_client(tmp_path), body).status_code == 422


def test_cloud_engine_without_key_is_409_when_private(tmp_path: Path) -> None:
    # Hors mode public : un moteur cloud sans clé tombe en 409 (indisponible),
    # pas en 403. Avec sa clé, il serait autorisé (modèle « clé posée → marche »).
    resp = _post(
        _client(tmp_path, public_mode=False), {"competitors": [{"engine": "openai"}]}
    )
    assert resp.status_code == 409


def test_public_mode_blocks_cloud_engine_403(tmp_path: Path) -> None:
    # Mode public (Space exposé) : fail-closed. Un moteur cloud est refusé en 403
    # AVANT toute vérif de clé/dispo — jamais d'appel facturé sur une instance
    # publique, clé présente ou non. (≠ 409 « indisponible » du mode privé.)
    resp = _post(
        _client(tmp_path, public_mode=True), {"competitors": [{"engine": "openai"}]}
    )
    assert resp.status_code == 403


def test_public_mode_blocks_cloud_llm_in_chain_403(tmp_path: Path) -> None:
    # Le LLM d'une chaîne OCR→LLM est aussi un kind référencé : un LLM cloud y est
    # gated en mode public, même derrière un moteur OCR gratuit (tesseract).
    body = {
        "competitors": [{"engine": "tesseract", "mode": "text_only", "llm": "openai"}]
    }
    resp = _post(_client(tmp_path, public_mode=True), body)
    assert resp.status_code == 403


def test_public_mode_allows_free_tesseract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # tesseract est le socle gratuit offert publiquement : il PASSE le gate public
    # (pas de 403). Binaire forcé absent → il tombe sur la dispo (409), prouvant
    # qu'il a franchi le verrou public et atteint la vérification runtime.
    monkeypatch.setattr(
        "xerocr.interfaces.web.app.engine_statuses",
        lambda **kw: engine_statuses(has_binary=lambda _name: None, **kw),
    )
    resp = _post(
        _client(tmp_path, public_mode=True), {"competitors": [{"engine": "tesseract"}]}
    )
    assert resp.status_code == 409


def test_demo_with_corpus_is_422(tmp_path: Path) -> None:
    # aucun concurrent (= démo) mais un corpus fourni → incohérent.
    client = _client(tmp_path)
    corpus_id = _upload_demo_corpus(client)
    assert _post(client, {"corpus_id": corpus_id}).status_code == 422


def test_unknown_corpus_is_404(tmp_path: Path) -> None:
    resp = _post(
        _client(tmp_path),
        {"competitors": [{"engine": "tesseract"}], "corpus_id": "nope"},
    )
    assert resp.status_code == 404


def test_unavailable_engine_is_409(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # binaire forcé absent → tesseract indisponible (déterministe), sans corpus.
    monkeypatch.setattr(
        "xerocr.interfaces.web.app.engine_statuses",
        lambda **kw: engine_statuses(has_binary=lambda _name: None, **kw),
    )
    resp = _post(_client(tmp_path), {"competitors": [{"engine": "tesseract"}]})
    assert resp.status_code == 409


def test_unknown_normalization_is_422(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # moteurs forcés disponibles → on atteint le plan ; profil inconnu → 422.
    monkeypatch.setattr(
        "xerocr.interfaces.web.app.engine_statuses",
        lambda **kw: engine_statuses(
            has_binary=lambda _n: "/usr/bin/tesseract",
            has_module=lambda _n: True,
            **kw,
        ),
    )
    client = _client(tmp_path)
    corpus_id = _upload_demo_corpus(client)
    resp = _post(
        client,
        {
            "competitors": [{"engine": "tesseract"}],
            "corpus_id": corpus_id,
            "normalization": "bogus",
        },
    )
    assert resp.status_code == 422


def test_precomputed_as_competitor_is_422(tmp_path: Path) -> None:
    # precomputed est le moteur de DÉMO, pas un concurrent OCR câblé → 422.
    client = _client(tmp_path)
    corpus_id = _upload_demo_corpus(client)
    resp = _post(
        client, {"competitors": [{"engine": "precomputed"}], "corpus_id": corpus_id}
    )
    assert resp.status_code == 422


def test_ocr_llm_chain_reaches_availability_not_preblocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # OCR→LLM n'est plus pré-bloqué (ex-422 « LLM non exposé »). tesseract forcé
    # dispo, openai indispo (pas de clé/SDK en CI) → 409 sur openai : la chaîne
    # atteint bien la garde de disponibilité.
    monkeypatch.setattr(
        "xerocr.interfaces.web.app.engine_statuses",
        lambda **kw: engine_statuses(
            has_binary=lambda _name: "/usr/bin/tesseract", **kw
        ),
    )
    client = _client(tmp_path)
    corpus_id = _upload_demo_corpus(client)
    resp = _post(
        client,
        {
            "competitors": [
                {"engine": "tesseract", "mode": "text_only", "llm": "openai"}
            ],
            "corpus_id": corpus_id,
        },
    )
    assert resp.status_code == 409
