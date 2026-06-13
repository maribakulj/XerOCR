"""Section carte des mots : matrice + regroupements verbatim, FR/EN, déterminisme."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    EngineWordError,
    WordError,
    WordErrorPayload,
)
from xerocr.evaluation.result import PipelineResult, RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.word_errors import WordErrorsSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _manifest() -> RunManifest:
    return RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )


def _result() -> RunResult:
    payload = WordErrorPayload(
        pipelines=("alpha", "beta", "gamma"),
        words=(
            WordError(
                word="prologve",
                total_errors=3,
                group="universal",
                per_engine=(
                    EngineWordError(pipeline="alpha", count=1, variant="prologue"),
                    EngineWordError(pipeline="beta", count=1, variant="prologe"),
                    EngineWordError(pipeline="gamma", count=1, variant="prolog"),
                ),
            ),
            WordError(
                word="roi",
                total_errors=2,
                group="engine_specific",
                per_engine=(
                    EngineWordError(pipeline="beta", count=2, variant="roy"),
                ),
            ),
            # Mot porteur d'un « & » : vérifie l'échappement (anti-XSS).
            WordError(
                word="m&t",
                total_errors=1,
                group="engine_specific",
                per_engine=(
                    EngineWordError(pipeline="alpha", count=1, variant="m+t"),
                ),
            ),
        ),
    )
    return RunResult(
        manifest=_manifest(),
        pipelines=(
            PipelineResult(pipeline="alpha", view="text"),
            PipelineResult(pipeline="beta", view="text"),
            PipelineResult(pipeline="gamma", view="text"),
        ),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def test_matrix_and_groups_render_words_verbatim_fr() -> None:
    html = WordErrorsSection().render(_result(), SectionContext(lang="fr"))
    assert html is not None
    assert "Carte des mots ratés" in html
    assert 'class="wmap-svg"' in html  # heatmap SVG présente
    # Mots de la GT **verbatim**.
    assert "prologve" in html and "roi" in html
    # G1 rend la **matrice** (comptes). La variante produite est collectée et
    # portée par le payload (enveloppe), mais son rendu dédié est l'incrément #3 —
    # pas encore affiché : la forme produite n'apparaît donc pas (encore).
    assert "prologue" not in html
    # Regroupements (libellés FR).
    assert "tous" in html and "un seul" in html
    # Comptes de la matrice (total + par moteur).
    assert ">3<" in html and ">2<" in html
    # Échappement défensif du mot porteur de « & ».
    assert "m&amp;t" in html
    # Déterminisme bit-à-bit du markup.
    assert html == WordErrorsSection().render(_result(), SectionContext(lang="fr"))


def test_renders_english_labels() -> None:
    html = WordErrorsSection().render(_result(), SectionContext(lang="en"))
    assert html is not None
    assert "Missed-word map" in html
    assert "all" in html and "one only" in html
    assert "prologve" in html  # mots verbatim, indépendants de la langue


def test_no_payload_returns_none() -> None:
    section = WordErrorsSection()
    assert section.render(RunResult(manifest=_manifest()), SectionContext()) is None
