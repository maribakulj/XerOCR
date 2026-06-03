"""Garde-fou anti-SSRF (sans réseau réel : IP littérales + résolveur mocké)."""

from __future__ import annotations

import socket

import pytest

from xerocr.adapters.corpus import _http
from xerocr.adapters.corpus._http import SsrfError, assert_public_url, fetch_json


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.org/x",  # schéma non http(s)
        "file:///etc/passwd",  # schéma local
        "http://user:pw@93.184.216.34/x",  # userinfo
        "http://127.0.0.1/x",  # loopback v4
        "http://[::1]/x",  # loopback v6
        "http://10.0.0.5/x",  # privé
        "http://192.168.1.1/x",  # privé
        "http://169.254.169.254/latest",  # link-local (métadonnées cloud)
        "https://0.0.0.0/x",  # non spécifié
    ],
)
def test_rejects_non_public_targets(url: str) -> None:
    with pytest.raises(SsrfError):
        assert_public_url(url)


def test_accepts_public_ip_literal() -> None:
    # IP publique littérale : aucune résolution réseau, aucune exception
    assert_public_url("http://93.184.216.34/manifest.json")


def test_rejects_hostname_resolving_to_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simule un nom qui résout vers l'interne (forme classique de SSRF/rebinding).
    def fake_getaddrinfo(host: str, *a: object, **k: object) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 80))]

    monkeypatch.setattr(_http.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SsrfError):
        assert_public_url("http://evil.test/x")


def test_fetch_json_guards_before_connecting() -> None:
    # La validation court-circuite tout I/O réseau pour une cible interdite.
    with pytest.raises(SsrfError):
        fetch_json("http://127.0.0.1/manifest.json")
