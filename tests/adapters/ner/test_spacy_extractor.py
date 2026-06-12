"""SpacyNerExtractor : contrat Module via spaCy injecté + fail-closed anti-silence.

Aucune dépendance réelle à spaCy : un faux ``nlp`` est injecté par ``loader``.
Le test clé est l'**anti-silence** : SDK/modèle absent → ``AdapterStepError``
(jamais ``[]``, le défaut de la source qui produisait un rappel 0 muet).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from xerocr.adapters.ner.spacy_extractor import SpacyNerExtractor
from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.errors import AdapterStepError
from xerocr.pipeline.run_control import RunControl
from xerocr.pipeline.types import RunContext


@dataclass
class _FakeEnt:
    label_: str
    start_char: int
    end_char: int
    text: str


class _FakeDoc:
    def __init__(self, ents: list[_FakeEnt]) -> None:
        self.ents = ents


class _FakeNlp:
    """Faux modèle spaCy : reconnaît « Marie » (PERSON) et « Paris » (GPE)."""

    meta = {"version": "3.7.0"}

    def __call__(self, text: str) -> _FakeDoc:
        ents: list[_FakeEnt] = []
        for needle, label in (("Marie", "PERSON"), ("Paris", "GPE")):
            idx = text.find(needle)
            if idx >= 0:
                ents.append(_FakeEnt(label, idx, idx + len(needle), needle))
        return _FakeDoc(ents)


def _context(tmp_path: Path) -> RunContext:
    return RunContext(
        document_id="d0",
        code_version="1.0",
        pipeline_name="alpha",
        workspace_uri=str(tmp_path),
    )


def _text_input(tmp_path: Path, text: str) -> dict[ArtifactType, Artifact]:
    path = tmp_path / "ocr.txt"
    path.write_text(text, encoding="utf-8")
    return {
        ArtifactType.RAW_TEXT: Artifact(
            id="d0:ocr:raw_text",
            document_id="d0",
            type=ArtifactType.RAW_TEXT,
            uri=str(path),
        )
    }


def test_produces_entities_artifact_with_text_and_mapped_labels(tmp_path: Path) -> None:
    extractor = SpacyNerExtractor(label="c0", loader=lambda _m: _FakeNlp())
    assert extractor.name == "ner:c0"
    assert extractor.output_types == frozenset({ArtifactType.ENTITIES})
    output = extractor.execute(
        _text_input(tmp_path, "Marie habite à Paris"),
        {},
        _context(tmp_path),
        RunControl(),
    )
    artifact = output.artifacts[ArtifactType.ENTITIES]
    assert artifact.type is ArtifactType.ENTITIES
    payload = json.loads(Path(artifact.uri).read_text(encoding="utf-8"))
    assert payload["text"] == "Marie habite à Paris"  # texte embarqué (R14)
    labels = {(e["label"], e["text"]) for e in payload["entities"]}
    # PERSON → PER, GPE → LOC (mapping HIPE/CoNLL).
    assert labels == {("PER", "Marie"), ("LOC", "Paris")}


def test_system_binaries_reports_versions_after_run(tmp_path: Path) -> None:
    extractor = SpacyNerExtractor(label="c0", loader=lambda _m: _FakeNlp())
    assert extractor.system_binaries() == {}  # rien chargé encore
    extractor.execute(
        _text_input(tmp_path, "Marie"), {}, _context(tmp_path), RunControl()
    )
    assert extractor.system_binaries()["spacy_model:fr_core_news_sm"] == "3.7.0"


def test_fail_closed_when_spacy_absent(tmp_path: Path) -> None:
    # Anti-silence : SDK absent (loader réel) → AdapterStepError « xerocr[ner] »,
    # jamais une liste vide. Skippé si spaCy est réellement installé (l'env
    # tomberait alors sur l'erreur de modèle, couverte séparément).
    import importlib.util

    if importlib.util.find_spec("spacy") is not None:
        pytest.skip("spaCy installé : le fail-closed SDK ne s'applique pas ici")
    extractor = SpacyNerExtractor(label="c0")  # loader=None → vrai chemin
    with pytest.raises(AdapterStepError, match=r"xerocr\[ner\]"):
        extractor.execute(
            _text_input(tmp_path, "Marie"), {}, _context(tmp_path), RunControl()
        )


def test_fail_closed_message_on_missing_model(tmp_path: Path) -> None:
    # spaCy présent mais modèle absent → AdapterStepError « spacy download »
    # (jamais un []). Faux module spaCy dont ``load`` lève OSError.
    import sys
    import types

    def _no_model(_model: str) -> object:
        raise OSError("model not found")

    fake_spacy = types.ModuleType("spacy")
    fake_spacy.__version__ = "3.7.0"  # type: ignore[attr-defined]
    fake_spacy.load = _no_model  # type: ignore[attr-defined]
    extractor = SpacyNerExtractor(label="c0")  # loader=None → import spacy
    sys.modules["spacy"] = fake_spacy
    try:
        with pytest.raises(AdapterStepError, match="spacy download"):
            extractor.execute(
                _text_input(tmp_path, "Marie"), {}, _context(tmp_path), RunControl()
            )
    finally:
        del sys.modules["spacy"]


def test_missing_text_input_raises(tmp_path: Path) -> None:
    extractor = SpacyNerExtractor(label="c0", loader=lambda _m: _FakeNlp())
    with pytest.raises(AdapterStepError, match="texte"):
        extractor.execute({}, {}, _context(tmp_path), RunControl())
