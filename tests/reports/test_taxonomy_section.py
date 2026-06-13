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
from xerocr.evaluation.result import PipelineResult, RunResult
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


def _two_engine_result() -> RunResult:
    # tess : visuel-lourd (6/10) ; pero : segmentation-lourd (7/10). Valeurs main.
    payload = TaxonomyPayload(
        classes=("case", "visual", "segmentation"),
        pipelines=(
            PipelineTaxonomy(
                pipeline="tess",
                total_errors=10,
                counts=(
                    TaxonomyCount(label="visual", count=6),
                    TaxonomyCount(label="case", count=4),
                ),
            ),
            PipelineTaxonomy(
                pipeline="pero",
                total_errors=10,
                counts=(
                    TaxonomyCount(label="segmentation", count=7),
                    TaxonomyCount(label="case", count=3),
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
        pipelines=(
            PipelineResult(pipeline="tess", view="text"),
            PipelineResult(pipeline="pero", view="text"),
        ),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def test_comparative_profile_compares_engines_per_class() -> None:
    html = TaxonomySection().render(_two_engine_result(), SectionContext(lang="fr"))
    assert html is not None
    assert "profil comparatif des moteurs" in html  # bloc #5 comparatif
    # Parts dérivées à la main : tess visuel 60 %, pero segmentation 70 %.
    assert "60%" in html and "70%" in html and "40%" in html and "30%" in html
    assert "segmentation" in html  # classe propre à pero, lue en ligne
    assert "·" in html  # classe absente chez un moteur (cellule vide)
    # Déterminisme bit-à-bit.
    assert html == TaxonomySection().render(_two_engine_result(), SectionContext("fr"))


def test_comparative_profile_is_bilingual_and_gated_on_two_engines() -> None:
    english = TaxonomySection().render(_two_engine_result(), SectionContext(lang="en"))
    assert english is not None and "comparative engine profile" in english
    # À 1 moteur, pas de comparaison → seule la barre empilée (pas de profil).
    assert "profil comparatif" not in (
        TaxonomySection().render(_result(), SectionContext()) or ""
    )
