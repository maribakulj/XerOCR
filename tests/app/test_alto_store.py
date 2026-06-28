"""``AltoStore`` : persistance par run, archive ZIP déterministe, sécurité chemin."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from cinoc.app.alto_store import AltoStore


def test_save_and_archive_roundtrip(tmp_path: Path) -> None:
    store = AltoStore(tmp_path)
    store.save("run-1", "doc-a", "tesseract", b"<alto>A</alto>")
    store.save("run-1", "doc-b", "tesseract", b"<alto>B</alto>")
    assert store.has("run-1")
    data = store.archive("run-1")
    assert data is not None
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        assert len(names) == 2
        assert all(n.endswith(".alto.xml") for n in names)
        payloads = sorted(archive.read(n) for n in names)
    assert payloads == [b"<alto>A</alto>", b"<alto>B</alto>"]


def test_archive_none_when_empty(tmp_path: Path) -> None:
    store = AltoStore(tmp_path)
    assert not store.has("absent")
    assert store.archive("absent") is None


def test_archive_is_deterministic(tmp_path: Path) -> None:
    store = AltoStore(tmp_path)
    store.save("run-1", "doc-b", "tesseract", b"B")
    store.save("run-1", "doc-a", "tesseract", b"A")
    first = store.archive("run-1")
    second = store.archive("run-1")
    assert first == second  # entrées triées → octets reproductibles


def test_runs_are_isolated(tmp_path: Path) -> None:
    store = AltoStore(tmp_path)
    store.save("run-1", "doc", "tesseract", b"one")
    store.save("run-2", "doc", "tesseract", b"two")
    assert store.has("run-1") and store.has("run-2")
    a1 = store.archive("run-1")
    a2 = store.archive("run-2")
    assert a1 is not None and a2 is not None
    with zipfile.ZipFile(io.BytesIO(a1)) as z:
        assert z.read(z.namelist()[0]) == b"one"
    with zipfile.ZipFile(io.BytesIO(a2)) as z:
        assert z.read(z.namelist()[0]) == b"two"


def test_path_traversal_run_id_is_contained(tmp_path: Path) -> None:
    # Un run_id hostile est slugifié → reste sous base_dir, jamais d'évasion.
    store = AltoStore(tmp_path / "base")
    store.save("../../escape", "doc", "tesseract", b"x")
    assert not (tmp_path / "escape").exists()
    assert store.has("../../escape")
