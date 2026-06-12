"""Section philologie : rendu lecture seule du payload ``philology``."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    MarkerPreservation,
    PhilologyPayload,
    PipelinePhilology,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.philology import PhilologySection

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


def test_renders_family_and_signs() -> None:
    payload = PhilologyPayload(
        pipelines=(
            PipelinePhilology(
                pipeline="eng",
                family="abbreviations",
                n_total=3,
                n_strict=1,
                n_expansion=3,
                markers=(
                    MarkerPreservation(sign="ꝑ", n_total=2, n_strict=1, n_expansion=2),
                    MarkerPreservation(sign="ꝓ", n_total=1, n_strict=0, n_expansion=1),
                ),
            ),
        )
    )
    html = PhilologySection().render(
        _result((Analysis(scope="corpus", view="text", payload=payload),)),
        SectionContext(),
    )
    assert html is not None
    assert "Philologie" in html
    assert "abréviations médiévales" in html
    assert "ꝑ" in html and "ꝓ" in html
    assert "33.3%" in html  # strict global 1/3
    assert "100.0%" in html  # expansion global 3/3


def test_without_payload_renders_nothing() -> None:
    assert PhilologySection().render(_result(()), SectionContext()) is None
