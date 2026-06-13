"""Qualité d'image (4d.1) : maths sur matrices construites à la main + bout en
bout via ``evaluate_run``. Aucune valeur n'est tirée de Picarones — toutes sont
dérivées au crayon (cf. commentaires). Le décodage PIL est exercé sur de vraies
images écrites par Pillow (``importorskip``)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import ImageQualityPayload
from xerocr.evaluation.image_quality import (
    composite_quality,
    estimate_rotation,
    gradient_noise,
    image_quality_analysis,
    laplacian_sharpness,
    measure_grayscale,
    michelson_contrast,
    quality_tier,
)
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics
from xerocr.evaluation.result import RunResult
from xerocr.evaluation.runner import evaluate_run

FIXED = datetime(2026, 1, 1, tzinfo=UTC)
TEXT_VIEW = EvaluationView(
    name="text",
    candidate_types=frozenset({ArtifactType.RAW_TEXT}),
    metric_names=("cer",),
)

#: « Tache » 4×4 : un seul pixel à 10 au milieu, le reste à 0. Toutes les valeurs
#: attendues ci-dessous en découlent au crayon (laplacien, gradients, percentiles).
SPECK = np.array(
    [[0, 0, 0, 0], [0, 10, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
    dtype=np.float64,
)


# --------------------------------------------------------------------------- #
# Maths (sans PIL) — matrices construites et valeurs dérivées à la main.
# --------------------------------------------------------------------------- #
def test_laplacian_sharpness_hand_derived() -> None:
    # Laplacien des 4 pixels intérieurs : [-40, 10, 10, 0] ; moyenne -5 ;
    # variance = (35²+15²+15²+5²)/4 = 1700/4 = 425 ; netteté = 425/500 = 0.85.
    assert laplacian_sharpness(SPECK) == 0.85


def test_flat_image_has_zero_sharpness() -> None:
    assert laplacian_sharpness(np.full((8, 8), 128.0)) == 0.0


def test_gradient_noise_speck_is_zero() -> None:
    # 24 gradients : quatre 10 (autour de la tache), vingt 0 → médiane 0.
    assert gradient_noise(SPECK) == 0.0


def test_gradient_noise_hand_derived_half() -> None:
    # [[0,30],[0,30]] : gradients horizontaux [30,30], verticaux [0,0] ;
    # médiane de [0,0,30,30] = (0+30)/2 = 15 ; bruit = 15/30 = 0.5.
    arr = np.array([[0, 30], [0, 30]], dtype=np.float64)
    assert gradient_noise(arr) == 0.5


def test_michelson_contrast_bimodal() -> None:
    # Colonnes 100/100/200/200 : p5 = 100, p95 = 200 → (200−100)/(200+100) = 1/3.
    arr = np.array([[100, 100, 200, 200]] * 4, dtype=np.float64)
    assert michelson_contrast(arr) == pytest.approx(1 / 3)


def test_michelson_contrast_uniform_is_zero() -> None:
    assert michelson_contrast(np.full((4, 4), 128.0)) == 0.0


def test_composite_quality_extremes() -> None:
    # 0.40·1 + 0.30·1 + 0.20·1 + 0.10·1 = 1.0 (approx : somme flottante) ;
    # tout à 0 → 0.20·1 + 0.10·1 = 0.30.
    assert composite_quality(1.0, 0.0, 0.0, 1.0) == pytest.approx(1.0)
    assert composite_quality(0.0, 0.0, 0.0, 0.0) == pytest.approx(0.30)


def test_composite_quality_rotation_penalty() -> None:
    # rotation contribue 0.10·max(0, 1−|rot|/10) : 5° → 0.05, ≥10° → 0.
    assert composite_quality(0.0, 0.0, 5.0, 0.0) == pytest.approx(0.25)
    assert composite_quality(0.0, 0.0, 10.0, 0.0) == pytest.approx(0.20)
    assert composite_quality(0.0, 0.0, 20.0, 0.0) == pytest.approx(0.20)


def test_composite_quality_mid() -> None:
    # 0.40·0.5 + 0.30·0.5 + 0.20·0.5 + 0.10·1 = 0.20+0.15+0.10+0.10 = 0.55.
    assert composite_quality(0.5, 0.5, 0.0, 0.5) == pytest.approx(0.55)


def test_quality_tier_thresholds() -> None:
    # Seuils ``≥`` (inclusifs) : 0.70 → good, 0.40 → medium.
    assert quality_tier(0.70) == "good"
    assert quality_tier(0.6999) == "medium"
    assert quality_tier(0.40) == "medium"
    assert quality_tier(0.3999) == "poor"
    assert quality_tier(1.0) == "good"
    assert quality_tier(0.0) == "poor"


def test_rotation_guard_small_image() -> None:
    # Image < 20 px → 0.0 (pas de fausse précision).
    assert estimate_rotation(np.full((10, 10), 128.0)) == 0.0


def test_rotation_bounded_and_integer() -> None:
    rotation = estimate_rotation(np.full((30, 30), 128.0))
    assert -5.0 <= rotation <= 5.0
    assert rotation == round(rotation)  # balayage par degré entier


def test_measure_grayscale_hand_derived() -> None:
    # netteté 0.85 · bruit 0 · contraste 1.0 (percentiles dégénérés) · rotation 0
    # (4 < 20) → qualité = 0.40·0.85 + 0.30·1 + 0.20·1 + 0.10·1 = 0.94 → good.
    measurement = measure_grayscale(SPECK)
    assert measurement.sharpness == 0.85
    assert measurement.noise == 0.0
    assert measurement.contrast == 1.0
    assert measurement.rotation_degrees == 0.0
    assert measurement.quality_score == 0.94
    assert measurement.tier == "good"


def test_measure_is_deterministic() -> None:
    assert measure_grayscale(SPECK) == measure_grayscale(SPECK)


# --------------------------------------------------------------------------- #
# Adaptativité : sans image lisible → pas d'analyse (jamais une mesure fabriquée).
# --------------------------------------------------------------------------- #
def test_no_image_uri_yields_no_analysis() -> None:
    corpus = CorpusSpec(name="c", documents=(DocumentRef(id="d1"),))
    assert image_quality_analysis("text", corpus) is None


def test_remote_image_uri_skipped() -> None:
    pytest.importorskip("PIL")
    corpus = CorpusSpec(
        name="c",
        documents=(DocumentRef(id="d1", image_uri="https://example.org/d1.jpg"),),
    )
    assert image_quality_analysis("text", corpus) is None


def test_missing_image_file_skipped(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    corpus = CorpusSpec(
        name="c",
        documents=(DocumentRef(id="d1", image_uri=str(tmp_path / "absent.png")),),
    )
    assert image_quality_analysis("text", corpus) is None


def test_non_decodable_bytes_skipped(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    path = tmp_path / "d1.png"
    path.write_bytes(b"\x89PNG pas vraiment une image")
    corpus = CorpusSpec(
        name="c", documents=(DocumentRef(id="d1", image_uri=str(path)),)
    )
    assert image_quality_analysis("text", corpus) is None


def test_pillow_absent_yields_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ``None`` dans ``sys.modules`` → ``from PIL import …`` lève ``ImportError``.
    monkeypatch.setitem(sys.modules, "PIL", None)
    corpus = CorpusSpec(
        name="c", documents=(DocumentRef(id="d1", image_uri=str(tmp_path / "x.png")),)
    )
    assert image_quality_analysis("text", corpus) is None


# --------------------------------------------------------------------------- #
# Bout en bout via ``evaluate_run`` (vraie image PNG décodée par Pillow).
# --------------------------------------------------------------------------- #
def _manifest() -> RunManifest:
    return RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=1,
        pipeline_specs=(
            PipelineSpec(name="eng", initial_inputs=(ArtifactType.IMAGE,)),
        ),
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )


def test_image_quality_through_evaluate_run(tmp_path: Path) -> None:
    pytest.importorskip("PIL")
    from PIL import Image

    image_path = tmp_path / "doc1.png"
    Image.new("L", (16, 16), color=128).save(image_path)  # gris plat
    gt = tmp_path / "doc1.gt.txt"
    gt.write_text("abcd", encoding="utf-8")
    hyp = tmp_path / "doc1.eng.txt"
    hyp.write_text("abcd", encoding="utf-8")
    document = DocumentRef(
        id="doc1",
        image_uri=str(image_path),
        ground_truths=(GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(gt)),),
    )
    corpus = CorpusSpec(name="c", documents=(document,))
    outputs = {
        "eng": {
            "doc1": {
                ArtifactType.RAW_TEXT: Artifact(
                    id="doc1:eng:raw_text",
                    document_id="doc1",
                    type=ArtifactType.RAW_TEXT,
                    uri=str(hyp),
                )
            }
        }
    }
    registry = MetricRegistry()
    register_default_metrics(registry)
    result = evaluate_run(
        corpus=corpus,
        evaluation=EvaluationSpec(views=(TEXT_VIEW,)),
        pipeline_outputs=outputs,
        registry=registry,
        manifest=_manifest(),
    )
    by_kind = {a.payload.kind: a for a in result.analyses}
    assert "image_quality" in by_kind
    analysis = by_kind["image_quality"]
    # Scope corpus, rattachée à la 1ʳᵉ vue (≠ par-pipeline, ≠ par-vue).
    assert analysis.scope == "corpus" and analysis.view == "text"
    payload = analysis.payload
    assert isinstance(payload, ImageQualityPayload)
    assert len(payload.documents) == 1
    measured = payload.documents[0]
    assert measured.document_id == "doc1"
    # Gris plat 16×16 : netteté/contraste/bruit = 0, rotation 0 (16 < 20) →
    # qualité = 0.20·1 + 0.10·1 = 0.30 → palier poor.
    assert measured.sharpness == 0.0
    assert measured.contrast == 0.0
    assert measured.noise == 0.0
    assert measured.rotation_degrees == 0.0
    assert measured.quality_score == 0.30
    assert measured.tier == "poor"
    assert payload.mean_quality == 0.30
    assert (payload.n_good, payload.n_medium, payload.n_poor) == (0, 0, 1)
    # Round-trip JSON : le payload structuré survit tel quel.
    reloaded = RunResult.model_validate_json(result.model_dump_json())
    assert reloaded.analyses == result.analyses


def test_single_payload_when_multiple_views(tmp_path: Path) -> None:
    # Qualité d'image = scope corpus, indépendante de la vue → **un seul** payload
    # même avec plusieurs vues (pas un par vue ; pas de relecture redondante).
    pytest.importorskip("PIL")
    from PIL import Image

    image_path = tmp_path / "d.png"
    Image.new("L", (16, 16), color=128).save(image_path)
    gt = tmp_path / "d.gt.txt"
    gt.write_text("abcd", encoding="utf-8")
    hyp = tmp_path / "d.eng.txt"
    hyp.write_text("abcd", encoding="utf-8")
    document = DocumentRef(
        id="d",
        image_uri=str(image_path),
        ground_truths=(GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(gt)),),
    )
    corpus = CorpusSpec(name="c", documents=(document,))
    outputs = {
        "eng": {
            "d": {
                ArtifactType.RAW_TEXT: Artifact(
                    id="d:eng:raw_text",
                    document_id="d",
                    type=ArtifactType.RAW_TEXT,
                    uri=str(hyp),
                )
            }
        }
    }
    second_view = EvaluationView(
        name="caseless",
        candidate_types=frozenset({ArtifactType.RAW_TEXT}),
        metric_names=("cer",),
        normalization_profile="caseless",
    )
    registry = MetricRegistry()
    register_default_metrics(registry)
    result = evaluate_run(
        corpus=corpus,
        evaluation=EvaluationSpec(views=(TEXT_VIEW, second_view)),
        pipeline_outputs=outputs,
        registry=registry,
        manifest=_manifest(),
    )
    image_quality = [
        a for a in result.analyses if isinstance(a.payload, ImageQualityPayload)
    ]
    assert len(image_quality) == 1
    assert image_quality[0].view == "text"  # rattachée à la 1ʳᵉ vue
