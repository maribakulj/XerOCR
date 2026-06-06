"""Garde-fou : un HuggingFace Space active le **mode public** par défaut.

Picarones déduisait le mode public de ``SPACE_ID`` (masquage des moteurs cloud,
refus des imports distants fetchant une URL côté serveur, verrouillage du code
tiers in-process). XerOCR ne lit ``SPACE_ID`` que pour la CSP (``headers.py``) :
sur un Space, ``_resolve_public_mode(None)`` renvoie ``False`` faute de
``XEROCR_PUBLIC_MODE`` explicite → surface cloud/SSRF/plugins ouverte.

L'override explicite (l'opérateur force ``public_mode=False``) doit, lui, rester
respecté — avant comme après la correction (test non-``xfail``).
"""

from __future__ import annotations

import pytest

from xerocr.interfaces.web.app import _resolve_public_mode


def test_explicit_choice_overrides_space(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPACE_ID", "user/space")
    assert _resolve_public_mode(False) is False
    assert _resolve_public_mode(True) is True


def test_space_defaults_to_public_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPACE_ID", "user/space")
    monkeypatch.delenv("XEROCR_PUBLIC_MODE", raising=False)
    assert _resolve_public_mode(None) is True
