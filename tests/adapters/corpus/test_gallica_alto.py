"""OCR Gallica via **ALTO** réel (Lot E) : extraction sur de vraies pages Gallica.

Fixtures : ALTO ``RequestDigitalElement`` de *Monsieur de Pourceaugnac* (Molière,
``ark:/12148/bpt6k5619759j``), vues f8 (dramatis personæ + acte I) et f10 (Julie).
On prouve l'extraction texte (``String/@CONTENT`` en ordre de lecture) + l'URL
ALTO exacte demandée, sans réseau.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.corpus import gallica as gallica_mod
from xerocr.adapters.corpus._http import HttpFetchError
from xerocr.adapters.corpus.gallica import GallicaImporter, alto_to_text
from xerocr.formats.alto import parse_alto

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "gallica_alto"


def _alto(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def test_alto_extraction_f8() -> None:
    text = alto_to_text(parse_alto(_alto("f8.alto.xml")))
    lines = text.splitlines()
    assert lines[0] == "MONSIEUR DE POURCEAUGNAC."
    assert len(lines) == 42  # même décompte que la fixture de référence
    assert "ACTE PREMIER" in text
    assert "ÉRASTE" in text


def test_alto_extraction_f10() -> None:
    text = alto_to_text(parse_alto(_alto("f10.alto.xml")))
    assert "JULIE." in text
    assert "Pourceaugnac" in text
    assert len(text.splitlines()) == 45


def test_fetch_ocr_text_requests_alto_and_extracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # fetch_bytes mické : on vérifie l'URL ALTO demandée ET le texte extrait.
    seen: dict[str, str] = {}

    def fake_fetch_bytes(url: str, *, timeout: float = 30.0, **_: object) -> bytes:
        seen["url"] = url
        return _alto("f8.alto.xml")

    monkeypatch.setattr(gallica_mod, "fetch_bytes", fake_fetch_bytes)
    imp = GallicaImporter("ark:/12148/bpt6k5619759j")
    text = imp.fetch_ocr_text(8)
    assert seen["url"] == (
        "https://gallica.bnf.fr/RequestDigitalElement?O=bpt6k5619759j&E=ALTO&Deb=8"
    )
    assert "MONSIEUR DE POURCEAUGNAC." in text


def test_fetch_ocr_text_returns_empty_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(url: str, **_: object) -> bytes:
        raise HttpFetchError("404")

    monkeypatch.setattr(gallica_mod, "fetch_bytes", boom)
    assert GallicaImporter("12148/x").fetch_ocr_text(3) == ""
