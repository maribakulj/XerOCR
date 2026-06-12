"""Section conformité HIPE : rendu lecture seule du payload ``hipe``."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    ConformityPayload,
    PipelineConformity,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.conformity import ConformitySection

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


def test_renders_scores_and_deltas() -> None:
    payload = ConformityPayload(
        hipe_view="hipe",
        raw_view="raw",
        heritage_view="heritage",
        pipelines=(
            PipelineConformity(
                pipeline="eng",
                cmer_micro=0.1234,
                cmer_macro=0.2,
                wmer_micro=0.3,
                wmer_macro=None,
                delta_norm=0.05,
                delta_heritage=None,
                n_missing=1,
            ),
        ),
    )
    html = ConformitySection().render(
        _result((Analysis(scope="corpus", view="hipe", payload=payload),)),
        SectionContext(),
    )
    assert html is not None
    assert "Conformité HIPE" in html
    assert "cmer_micro" in html and "wmer_macro" in html  # noms du scorer
    assert "0.1234" in html and "+0.0500" in html
    assert html.count("—") >= 2  # wmer_macro et delta_heritage absents → tiret
    assert "eng" in html


def test_without_payload_renders_nothing() -> None:
    assert ConformitySection().render(_result(()), SectionContext()) is None
