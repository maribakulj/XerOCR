"""Chargement de représentation : texte via la couche 2, types non gérés."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.representations import load_representation


def test_loads_raw_text_and_normalises_newlines(tmp_path: Path) -> None:
    path = tmp_path / "t.txt"
    # write_bytes (pas write_text) : octets EXACTS. write_text traduit \n → \r\n
    # sous Windows, ce qui fausserait ce test de normalisation des fins de ligne
    # (le lecteur lit en binaire via read_bytes).
    path.write_bytes("héllo\r\nworld".encode())
    assert load_representation(str(path), ArtifactType.RAW_TEXT) == "héllo\nworld"


def test_unsupported_type_raises(tmp_path: Path) -> None:
    path = tmp_path / "x.bin"
    path.write_bytes(b"x")
    with pytest.raises(EvaluationError):
        load_representation(str(path), ArtifactType.LAYOUT)
