"""Calibration : ECE/MCE + analyse — valeurs dérivées **à la main** (§5.8b)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.evaluation.calibration import (
    calibration_analysis,
    calibration_from_pairs,
    load_confidence_tokens,
)


def test_ece_mce_hand_computed() -> None:
    # 4 jetons, un par bin : (0.95,T)=écart .05 ; (0.85,T)=.15 ; (0.75,F)=.75 ;
    # (0.05,F)=.05. ECE = ¼·(.05+.15+.75+.05)=0.25 ; MCE = 0.75.
    pairs = [(0.95, True), (0.85, True), (0.75, False), (0.05, False)]
    ece, mce, bins = calibration_from_pairs(pairs)
    assert ece == pytest.approx(0.25)
    assert mce == pytest.approx(0.75)
    assert len(bins) == 4
    assert all(b.count == 1 for b in bins)


def test_perfectly_calibrated_bin() -> None:
    # Bin [0.8;0.9[ : confiances 0.8/0.8/0.8/0.8/0.8, 4 corrects sur 5 → acc 0.8
    # = confiance moyenne → ECE 0.
    pairs = [(0.8, True)] * 4 + [(0.8, False)]
    ece, mce, bins = calibration_from_pairs(pairs)
    assert ece == pytest.approx(0.0)
    assert mce == pytest.approx(0.0)
    assert bins[0].accuracy == pytest.approx(0.8)


def _setup(tmp_path: Path, tokens: list[dict[str, object]]) -> tuple[CorpusSpec, dict]:
    gt = tmp_path / "d1.gt.txt"
    gt.write_text("le chat noir", encoding="utf-8")
    sidecar = tmp_path / "d1.confidences.json"
    sidecar.write_text(json.dumps(tokens), encoding="utf-8")
    corpus = CorpusSpec(
        name="c",
        documents=(
            DocumentRef(
                id="d1",
                ground_truths=(
                    GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(gt)),
                ),
            ),
        ),
    )
    outputs = {
        "tess": {
            "d1": {
                ArtifactType.CONFIDENCES: Artifact(
                    id="d1:tess:confidences",
                    document_id="d1",
                    type=ArtifactType.CONFIDENCES,
                    uri=str(sidecar),
                )
            }
        }
    }
    return corpus, outputs


def test_analysis_scores_tokens_against_reference_multiset(tmp_path: Path) -> None:
    # « chat » (0.9) est dans la GT → correct ; « chien » (0.7) absent → faux.
    corpus, outputs = _setup(
        tmp_path,
        [
            {"text": "chat", "confidence": 0.9},
            {"text": "chien", "confidence": 0.7},
        ],
    )
    analysis = calibration_analysis("text", corpus, outputs)
    assert analysis is not None
    row = analysis.payload.pipelines[0]  # type: ignore[union-attr]
    assert row.pipeline == "tess" and row.n_tokens == 2
    # Écarts : |1−0.9|=0.1 et |0−0.7|=0.7 → ECE ½·0.8 = 0.4 ; MCE 0.7.
    assert row.ece == pytest.approx(0.4)
    assert row.mce == pytest.approx(0.7)


def test_no_sidecar_yields_none(tmp_path: Path) -> None:
    corpus, outputs = _setup(tmp_path, [])
    assert calibration_analysis("text", corpus, outputs) is None


def test_unreadable_sidecar_degrades_to_empty() -> None:
    artifact = Artifact(
        id="x", document_id="d1", type=ArtifactType.CONFIDENCES,
        uri="/nonexistent/conf.json",
    )
    assert load_confidence_tokens(artifact) == []
