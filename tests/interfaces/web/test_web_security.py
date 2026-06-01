"""Sécurité HTTP de la vitrine : en-têtes (CSP stricte) + limiteur de débit."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from xerocr.interfaces.web.app import create_app
from xerocr.interfaces.web.security.headers import (
    CONTENT_SECURITY_POLICY,
    SecurityHeadersMiddleware,
    get_csp_policy,
    is_huggingface_space,
)
from xerocr.interfaces.web.security.rate_limit import RateLimitMiddleware


def _client(tmp_path: Path, rate_limit: int = 60) -> TestClient:
    return TestClient(create_app(reports_dir=tmp_path, rate_limit=rate_limit))


def test_security_headers_present(tmp_path: Path) -> None:
    resp = _client(tmp_path).get("/health")
    assert resp.headers["content-security-policy"] == CONTENT_SECURITY_POLICY
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"


def test_csp_is_strict() -> None:
    # default-src verrouillé ; aucun script autorisé (le rapport n'a que du CSS).
    assert "default-src 'none'" in CONTENT_SECURITY_POLICY
    assert "frame-ancestors 'none'" in CONTENT_SECURITY_POLICY
    assert "script-src" not in CONTENT_SECURITY_POLICY  # → tombe sur default 'none'


def test_is_huggingface_space_reads_space_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # SPACE_ID injecté par HF = marqueur de Space ; absent/blanc = local.
    monkeypatch.delenv("SPACE_ID", raising=False)
    assert is_huggingface_space() is False
    monkeypatch.setenv("SPACE_ID", "Ma-Ri-Ba-Ku/XerOCR")
    assert is_huggingface_space() is True
    monkeypatch.setenv("SPACE_ID", "   ")  # valeur blanche ⇒ pas un Space
    assert is_huggingface_space() is False


def test_headers_locked_without_space_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Hors Space : verrou total anti-cadrage ('none' + X-Frame-Options: DENY).
    monkeypatch.delenv("SPACE_ID", raising=False)
    resp = _client(tmp_path).get("/health")
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
    assert resp.headers["x-frame-options"] == "DENY"


def test_csp_relaxes_frame_ancestors_on_hf_space(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sur HF Space, la vitrine doit être embarquable dans l'iframe du Hub :
    # frame-ancestors ouvre huggingface.co / *.hf.space, sans 'none'.
    monkeypatch.setenv("SPACE_ID", "Ma-Ri-Ba-Ku/XerOCR")
    resp = _client(tmp_path).get("/health")
    csp = resp.headers["content-security-policy"]
    assert csp == get_csp_policy()
    assert "huggingface.co" in csp and "*.hf.space" in csp
    # le verrou 'none' ne doit plus s'appliquer à frame-ancestors
    assert "'none'" not in csp.split("frame-ancestors", 1)[1]
    # le reste de la CSP stricte est intact (aucune ressource externe tolérée)
    assert "default-src 'none'" in csp


def test_x_frame_options_omitted_on_hf_space(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # X-Frame-Options: DENY a priorité absolue sur frame-ancestors dans les
    # vieux navigateurs → il est omis en Space pour ne pas annuler l'embed.
    monkeypatch.setenv("SPACE_ID", "Ma-Ri-Ba-Ku/XerOCR")
    resp = _client(tmp_path).get("/health")
    assert "x-frame-options" not in resp.headers


def test_headers_on_html_report(tmp_path: Path) -> None:
    from xerocr.app.results import dump_run_result
    from xerocr.domain.run import RunManifest, utcnow
    from xerocr.evaluation.result import RunResult

    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=0,
        code_version="1.0",
        started_at=utcnow(),
        completed_at=utcnow(),
    )
    dump_run_result(RunResult(manifest=manifest), tmp_path / "r.json")
    resp = _client(tmp_path).get("/reports/r")
    assert resp.status_code == 200
    assert "content-security-policy" in resp.headers  # durci aussi sur le rapport


def test_rate_limit_returns_429(tmp_path: Path) -> None:
    client = _client(tmp_path, rate_limit=3)
    statuses = [client.get("/health").status_code for _ in range(5)]
    assert statuses[:3] == [200, 200, 200]
    assert statuses[3:] == [429, 429]


def test_rate_limit_rejects_invalid_config() -> None:
    with pytest.raises(ValueError):
        create_app(rate_limit=0)


def test_rate_limit_middleware_guards_its_own_config() -> None:
    async def _noop(scope: object, receive: object, send: object) -> None:
        return None

    with pytest.raises(ValueError):
        RateLimitMiddleware(_noop, max_requests=0)  # type: ignore[arg-type]


def test_middlewares_pass_non_http_scope_through() -> None:
    # scope non-HTTP (lifespan/websocket) : traversée intacte, aucun en-tête,
    # aucun comptage de débit.
    seen: list[str] = []

    async def _app(scope: dict[str, object], receive: object, send: object) -> None:
        seen.append(str(scope["type"]))

    async def _noop_send(message: object) -> None:
        return None

    scope: dict[str, object] = {"type": "lifespan"}
    asyncio.run(SecurityHeadersMiddleware(_app)(scope, _noop_send, _noop_send))
    asyncio.run(RateLimitMiddleware(_app)(scope, _noop_send, _noop_send))
    assert seen == ["lifespan", "lifespan"]


def test_rate_limit_counts_unknown_client() -> None:
    # scope HTTP sans 'client' → IP 'unknown', toujours borné (pas de crash).
    sent: list[int] = []

    async def _app(scope: dict[str, object], receive: object, send: object) -> None:
        sent.append(200)

    async def _capture(message: dict[str, object]) -> None:
        if message["type"] == "http.response.start":
            sent.append(int(message["status"]))  # type: ignore[call-overload]

    mw = RateLimitMiddleware(_app, max_requests=1)
    scope: dict[str, object] = {"type": "http"}  # pas de 'client'
    asyncio.run(mw(scope, _capture, _capture))
    asyncio.run(mw(scope, _capture, _capture))
    assert 200 in sent and 429 in sent
