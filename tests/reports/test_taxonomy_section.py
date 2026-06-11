"""Section taxonomie : lecture seule, parts relatives, rendu déterministe."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    PipelineTaxonomy,
    TaxonomyCount,
    TaxonomyPayload,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import Section, SectionContext
from xerocr.reports.sections.taxonomy import TaxonomySection

FIXED = datetime(2026, 6, 1, tzinfo=UTC)


def _result() -> RunResult:
    payload = TaxonomyPayload(
        classes=("case", "visual", "other"),
        pipelines=(
            PipelineTaxonomy(
                pipeline="tess",
                total_errors=4,
                counts=(
                    TaxonomyCount(label="visual", count=3),
                    TaxonomyCount(label="case", count=1),
                ),
            ),
        ),
    )
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=1,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def test_satisfies_section_protocol() -> None:
    section = TaxonomySection()
    assert isinstance(section, Section)
    assert section.name == "taxonomy"


def test_renders_composition_bar_and_legend() -> None:
    html = TaxonomySection().render(_result(), SectionContext())
    assert html is not None
    assert 'class="comp-bar"' in html  # barre empilée SVG
    assert 'class="comp-legend"' in html and 'class="comp-row"' in html
    assert "visual" in html and "75%" in html  # 3/4 dérivé à la main
    assert "25%" in html
    assert html == TaxonomySection().render(_result(), SectionContext())


def test_without_payload_renders_nothing() -> None:
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=0,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    assert (
        TaxonomySection().render(RunResult(manifest=manifest), SectionContext())
        is None
    )
