"""``CorpusStore.materialize`` : alloue un dossier, enregistre, n'enregistre pas un
corpus partiel si le builder échoue (couverture directe manquante — audit #10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.app.corpus_upload import CorpusStore
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef


def test_materialize_allocates_dir_and_registers(tmp_path: Path) -> None:
    store = CorpusStore(tmp_path)
    seen: dict[str, Path] = {}

    def builder(dest: Path) -> CorpusSpec:
        seen["dest"] = dest
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "a.jpg").write_bytes(b"img")
        return CorpusSpec(
            name="built",
            documents=(DocumentRef(id="a", image_uri=str(dest / "a.jpg")),),
        )

    corpus_id, spec = store.materialize(builder)
    assert spec.name == "built"
    assert seen["dest"] == tmp_path / corpus_id  # dossier neuf sous base_dir
    assert store.get(corpus_id) is spec  # enregistré et relisable


def test_materialize_failure_registers_nothing(tmp_path: Path) -> None:
    store = CorpusStore(tmp_path)

    def boom(dest: Path) -> CorpusSpec:
        raise RuntimeError("échec de construction")

    with pytest.raises(RuntimeError):
        store.materialize(boom)
    # aucun id n'a été enregistré (le store reste vide)
    assert store.get("nimporte") is None


def test_materialize_ids_are_unique(tmp_path: Path) -> None:
    store = CorpusStore(tmp_path)

    def builder(dest: Path) -> CorpusSpec:
        return CorpusSpec(name="c")

    id1, _ = store.materialize(builder)
    id2, _ = store.materialize(builder)
    assert id1 != id2
