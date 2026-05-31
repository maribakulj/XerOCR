"""``load_run_spec`` : YAML valide → ``RunSpec`` (chemins sécurisés) ; rejets."""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.app.loader import RunSpecError, load_run_spec
from xerocr.app.security import PathSecurityError

_VALID = """
run_id: demo
corpus:
  name: my_corpus
  documents:
    - id: doc1
      image_uri: images/doc1.png
      ground_truths:
        - {type: raw_text, uri: gt/doc1.txt}
pipelines:
  - name: tess
    initial_inputs: [image]
    steps:
      - id: ocr
        kind: ocr
        adapter_name: "tesseract:fra"
        input_types: [image]
        output_types: [raw_text]
adapter_kwargs:
  "tesseract:fra": {label: fra, lang: fra}
evaluation:
  views:
    - {name: text, candidate_types: [raw_text], metric_names: [cer, wer]}
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "run.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_valid_run_spec(tmp_path: Path) -> None:
    # la vérité-terrain doit exister (must_exist=True) ; l'image, non.
    (tmp_path / "gt").mkdir()
    (tmp_path / "gt" / "doc1.txt").write_text("réf", encoding="utf-8")
    spec = load_run_spec(_write(tmp_path, _VALID))
    assert spec.run_id == "demo"
    assert spec.corpus.name == "my_corpus"
    assert len(spec.pipelines) == 1
    assert spec.adapter_kwargs["tesseract:fra"]["lang"] == "fra"
    document = spec.corpus.documents[0]
    assert document.image_uri == str((tmp_path / "images/doc1.png").resolve())
    assert document.ground_truths[0].uri == str((tmp_path / "gt/doc1.txt").resolve())


def test_path_traversal_rejected(tmp_path: Path) -> None:
    evil = _VALID.replace("images/doc1.png", "../../../etc/passwd")
    with pytest.raises(PathSecurityError):
        load_run_spec(_write(tmp_path, evil))


def test_missing_ground_truth_rejected(tmp_path: Path) -> None:
    # GT inexistante → erreur typée AU CHARGEMENT (pas un OSError opaque en run).
    with pytest.raises(PathSecurityError):
        load_run_spec(_write(tmp_path, _VALID))


def test_malformed_yaml_rejected(tmp_path: Path) -> None:
    with pytest.raises(RunSpecError):
        load_run_spec(_write(tmp_path, "just a string"))


def test_unknown_field_rejected(tmp_path: Path) -> None:
    with pytest.raises(RunSpecError):
        load_run_spec(_write(tmp_path, _VALID + "\nbogus_field: 1\n"))
