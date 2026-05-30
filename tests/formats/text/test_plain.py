"""Tests du lecteur de texte brut."""

from __future__ import annotations

from xerocr.formats.text.plain import read_plaintext


def test_decodes_utf8() -> None:
    assert read_plaintext("héllo".encode()) == "héllo"


def test_strips_utf8_bom() -> None:
    assert read_plaintext(b"\xef\xbb\xbfabc") == "abc"


def test_normalizes_line_endings() -> None:
    assert read_plaintext(b"a\r\nb\rc\n") == "a\nb\nc\n"


def test_respects_encoding() -> None:
    assert read_plaintext("café".encode("latin-1"), encoding="latin-1") == "café"
