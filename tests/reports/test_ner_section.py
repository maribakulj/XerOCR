"""Section ner : F1 global + par catégorie + échantillons, ``None`` sans payload."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    EntityCategoryScore,
    EntityMention,
    NerPayload,
    PipelineNer,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.ner import NerSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _manifest() -> RunManifest:
    return RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=2,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )


def _result() -> RunResult:
    payload = NerPayload(
        iou_threshold=0.5,
        pipelines=(
            PipelineNer(
                pipeline="alpha",
                n_reference=10,
                true_positives=7,
                false_positives=2,
                false_negatives=3,
                precision=7 / 9,
                recall=0.7,
                f1=0.737,
                per_category=(
                    EntityCategoryScore(
                        label="PER", precision=0.8, recall=0.75, f1=0.77, support=8
                    ),
                ),
                missed=(EntityMention(label="LOC", text="Bourgogne"),),
                hallucinated=(EntityMention(label="PER", text="Charles"),),
            ),
        ),
    )
    return RunResult(
        manifest=_manifest(),
        analyses=(Analysis(scope="corpus", view="entities", payload=payload),),
    )


def test_renders_global_categories_and_samples() -> None:
    html = NerSection().render(_result(), SectionContext())
    assert html is not None
    assert "Entités nommées" in html
    assert "conjointe" in html  # caveat OCR + NER documenté
    assert "alpha" in html
    assert "70.0%" in html  # rappel global
    assert "7/2/3" in html  # TP/FP/FN
    assert "PER" in html and "support" in html  # bloc par catégorie
    assert "Bourgogne (LOC)" in html  # entité manquée
    assert "Charles (PER)" in html  # entité hallucinée
    # Déterminisme bit-à-bit.
    assert html == NerSection().render(_result(), SectionContext())


def test_no_payload_returns_none() -> None:
    section = NerSection()
    assert section.render(RunResult(manifest=_manifest()), SectionContext()) is None
