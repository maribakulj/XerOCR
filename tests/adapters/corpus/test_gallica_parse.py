"""Gallica pur (sans réseau) : normalisation ARK, détection HTML, URL manifeste."""

from __future__ import annotations

import pytest

from xerocr.adapters.corpus.gallica import (
    GallicaArkError,
    GallicaImporter,
    _looks_like_html,
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


def test_looks_like_html() -> None:
    assert _looks_like_html("<!DOCTYPE html><html>…")
    assert _looks_like_html("<html lang='fr'>")
    assert not _looks_like_html("Texte OCR brut de la vue.")


def test_manifest_url() -> None:
    imp = GallicaImporter("ark:/12148/btv1b8453561w")
    assert imp.manifest_url == (
        "https://gallica.bnf.fr/ark:/12148/btv1b8453561w/manifest.json"
    )
    assert imp.ark == "12148/btv1b8453561w"
