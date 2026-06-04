"""Parsing eScriptorium pur (sélection de couche GT, URL d'image) — sans réseau."""

from __future__ import annotations

from xerocr.adapters.corpus.escriptorium import _image_uri, extract_gt_text


def test_gt_from_lines() -> None:
    transcriptions = [
        {
            "transcription": {"name": "manual"},
            "lines": [{"content": "a"}, {"content": "b"}, {"content": ""}],
        }
    ]
    assert extract_gt_text(transcriptions, "manual") == "a\nb"


def test_gt_from_content_field() -> None:
    transcriptions = [{"name": "manual", "content": "hello world"}]
    assert extract_gt_text(transcriptions, "manual") == "hello world"


def test_gt_layer_selection() -> None:
    transcriptions = [
        {"transcription": {"name": "ocr"}, "content": "bruit OCR"},
        {"transcription": {"name": "manual"}, "content": "vérité"},
    ]
    assert extract_gt_text(transcriptions, "manual") == "vérité"


def test_gt_missing_layer_returns_empty() -> None:
    transcriptions = [{"transcription": {"name": "manual"}, "content": "x"}]
    assert extract_gt_text(transcriptions, "ghost") == ""


def test_gt_empty_layer_takes_first() -> None:
    transcriptions = [{"name": "whatever", "content": "premier"}]
    assert extract_gt_text(transcriptions, "") == "premier"


def test_image_uri_object_form_is_joined() -> None:
    assert _image_uri({"image": {"uri": "/media/x.png"}}, "http://e.org") == (
        "http://e.org/media/x.png"
    )


def test_image_uri_absolute_string_kept() -> None:
    assert _image_uri({"image": "https://abs.org/y.jpg"}, "http://e.org") == (
        "https://abs.org/y.jpg"
    )


def test_image_uri_missing_is_empty() -> None:
    assert _image_uri({}, "http://e.org") == ""
