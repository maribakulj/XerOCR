"""Gallica pur (sans réseau) : normalisation ARK, vue, URLs manifeste IIIF + ALTO."""

from __future__ import annotations

import pytest

from xerocr.adapters.corpus.gallica import (
    GallicaArkError,
    GallicaImporter,
    normalize_ark,
    vue_number,
)


def test_vue_number_from_image_url() -> None:
    url = "https://gallica.bnf.fr/iiif/ark:/12148/btv1bX/f7/full/full/0/native.jpg"
    assert vue_number(url) == 7
    assert vue_number("http://127.0.0.1/iiif/1.png") is None  # repli position


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("12148/btv1b8453561w", "12148/btv1b8453561w"),
        ("ark:/12148/btv1b8453561w", "12148/btv1b8453561w"),
        ("ark:/12148/btv1b8453561w/", "12148/btv1b8453561w"),
        ("  12148/x.y-z  ", "12148/x.y-z"),
    ],
)
def test_normalize_ark_variants(raw: str, expected: str) -> None:
    assert normalize_ark(raw) == expected


@pytest.mark.parametrize("bad", ["", "   ", "notanark", "12148/bad space", "/12148/"])
def test_normalize_ark_rejects_malformed(bad: str) -> None:
    with pytest.raises(GallicaArkError):
        normalize_ark(bad)


def test_manifest_url_has_iiif_prefix() -> None:
    # Le manifeste IIIF Gallica est sous /iiif/ (sans le préfixe → 403 en prod).
    imp = GallicaImporter("ark:/12148/bpt6k5619759j")
    assert imp.manifest_url == (
        "https://gallica.bnf.fr/iiif/ark:/12148/bpt6k5619759j/manifest.json"
    )
    assert imp.ark == "12148/bpt6k5619759j"


def test_alto_url_uses_request_digital_element() -> None:
    # OCR via l'endpoint ALTO officiel ; O = identifiant seul (sans le naID 12148).
    imp = GallicaImporter("ark:/12148/bpt6k5619759j")
    assert imp.alto_url(8) == (
        "https://gallica.bnf.fr/RequestDigitalElement?O=bpt6k5619759j&E=ALTO&Deb=8"
    )
