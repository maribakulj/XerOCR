"""Section données structurées : rendu lecture seule du payload."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    CategoryBreakdown,
    PipelineStructuredData,
    StructuredDataPayload,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.structured_data import StructuredDataSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result(analyses: tuple[Analysis, ...]) -> RunResult:
    manifest = RunManifest(
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
    return RunResult(manifest=manifest, analyses=analyses)


def test_renders_categories_and_lost_forms() -> None:
    payload = StructuredDataPayload(
        pipelines=(
            PipelineStructuredData(
                pipeline="eng",
                categories=(
                    CategoryBreakdown(
                        category="year",
                        n_total=2,
                        n_strict=1,
                        n_value=1,
                        strict_score=0.5,
                        value_score=0.5,
                        lost=("1789",),
                    ),
                    CategoryBreakdown(
                        category="foliation",
                        n_total=1,
                        n_strict=0,
                        n_value=1,
                        strict_score=0.0,
                        value_score=1.0,
                    ),
                ),
            ),
        )
    )
    html = StructuredDataSection().render(
        _result((Analysis(scope="corpus", view="text", payload=payload),)),
        SectionContext(),
    )
    assert html is not None
    assert "Données structurées" in html
    assert "années" in html and "foliotation" in html
    assert "50.0%" in html and "100.0%" in html
    assert "1789" in html  # forme perdue affichée


def test_renders_english_labels() -> None:
    payload = StructuredDataPayload(
        pipelines=(
            PipelineStructuredData(
                pipeline="eng",
                categories=(
                    CategoryBreakdown(
                        category="year",
                        n_total=2,
                        n_strict=1,
                        n_value=1,
                        strict_score=0.5,
                        value_score=0.5,
                        lost=("1789",),
                    ),
                ),
            ),
        )
    )
    html = StructuredDataSection().render(
        _result((Analysis(scope="corpus", view="text", payload=payload),)),
        SectionContext(lang="en"),
    )
    assert html is not None
    assert "Structured data" in html and "Données structurées" not in html
    assert "numeric sequences" in html and "séquences numériques" not in html
    assert "years" in html and "années" not in html


def test_without_payload_renders_nothing() -> None:
    assert StructuredDataSection().render(_result(()), SectionContext()) is None
