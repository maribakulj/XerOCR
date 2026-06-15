"""Section bilan de correction : rendu lecture seule du payload ``correction``."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    CorrectionPayload,
    OverNormalizedWord,
    PipelineCorrection,
    RegressionSample,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.correction import CorrectionSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result(analyses: tuple[Analysis, ...]) -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=2,
        pipeline_specs=(
            PipelineSpec(name="chain", initial_inputs=(ArtifactType.IMAGE,)),
        ),
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(manifest=manifest, analyses=analyses)


def _payload() -> CorrectionPayload:
    return CorrectionPayload(
        metric="cmer",
        catastrophic_threshold=0.10,
        overedit_threshold=2.0,
        insertion_threshold=0.10,
        edit_run_threshold=20,
        pipelines=(
            PipelineCorrection(
                pipeline="chain",
                n_documents=2,
                n_missing_corrected=1,
                improvement_rate=0.5,
                regression_rate=0.5,
                no_change_rate=0.0,
                pref_score=0.0,
                n_catastrophic=1,
                catastrophic_rate=0.5,
                pcis_macro=-0.1212,
                pcis_median=-0.1212,
                ccr=2 / 15,
                change_ratio=2.0,
                length_ratio=1.0,
                char_ins_ratio=0.0,
                corrected=1,
                introduced=1,
                net_improvement=0,
                corrected_samples=("chat",),
                introduced_samples=("abc",),
                n_correct_ocr_words=3,
                n_over_normalized=1,
                over_normalization=1 / 3,
                over_normalized_samples=(
                    OverNormalizedWord(
                        document_id="doc2", reference="abc", corrected="abx"
                    ),
                ),
                edit_run_median=1.0,
                edit_run_max=1,
                edit_run_share=0.0,
                worst_regressions=(
                    RegressionSample(
                        document_id="doc2",
                        cmer_raw=0.0,
                        cmer_corrected=1 / 3,
                        delta=1 / 3,
                    ),
                ),
            ),
        ),
    )


def test_renders_balance_and_samples() -> None:
    html = CorrectionSection().render(
        _result((Analysis(scope="corpus", view="text", payload=_payload()),)),
        SectionContext(),
    )
    assert html is not None
    assert "Bilan de correction" in html
    assert "chain" in html and "50.0%" in html
    assert "+0.0000" in html  # pref signé
    assert "2.0000" in html  # change_ratio
    assert "Pires régressions" in html and "doc2" in html
    # #16 sur-normalisation : flux mot OCR-juste (référence) → forme du correcteur.
    assert "Mots sur-normalisés" in html and 'class="wf-row"' in html
    assert 'class="wf-word wf-src">abc</span>' in html and "abx" in html
    assert "R-1.8" in html  # étages matérialisés vides signalés


def test_renders_english_labels() -> None:
    html = CorrectionSection().render(
        _result((Analysis(scope="corpus", view="text", payload=_payload()),)),
        SectionContext(lang="en"),
    )
    assert html is not None
    assert "Correction balance" in html  # <h2>
    assert "Worst regressions" in html  # résumé du détail des régressions
    assert "Over-normalized words" in html  # #16 sur-normalisation
    assert "cmer corrected" in html  # en-tête de table
    # Les libellés FR correspondants sont absents.
    assert "Bilan de correction" not in html
    assert "Pires régressions" not in html
    assert "Mots sur-normalisés" not in html
    assert "cmer corrigé" not in html


def test_without_payload_renders_nothing() -> None:
    assert CorrectionSection().render(_result(()), SectionContext()) is None
