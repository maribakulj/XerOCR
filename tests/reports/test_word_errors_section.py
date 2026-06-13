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
    # #3 forme produite : la variante dominante (portée par le payload) est
    # désormais rendue — la forme produite apparaît, verbatim (rien d'inventé).
    assert "forme produite par moteur" in html
    assert "prologue" in html and "prolog" in html and "roy" in html
    # #2 recouvrement inter-moteurs + regroupements (libellés FR).
    assert "recouvrement inter-moteurs" in html
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
    assert "cross-engine overlap" in html  # bloc #2
    assert "produced form per engine" in html  # bloc #3
    assert "prologve" in html  # mots verbatim, indépendants de la langue


def _overlap_result() -> RunResult:
    # 4 moteurs : « shared » raté par a+b+c (3/4 → partiel), « lonely » par a seul.
    payload = WordErrorPayload(
        pipelines=("a", "b", "c", "d"),
        words=(
            WordError(
                word="shared",
                total_errors=3,
                group="partial",
                per_engine=(
                    EngineWordError(pipeline="a", count=1, variant="x"),
                    EngineWordError(pipeline="b", count=1, variant="y"),
                    EngineWordError(pipeline="c", count=1, variant="z"),
                ),
            ),
            WordError(
                word="lonely",
                total_errors=1,
                group="engine_specific",
                per_engine=(EngineWordError(pipeline="a", count=1, variant="q"),),
            ),
        ),
    )
    return RunResult(
        manifest=_manifest(),
        pipelines=tuple(
            PipelineResult(pipeline=name, view="text") for name in ("a", "b", "c", "d")
        ),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def test_overlap_groups_words_by_engine_signature() -> None:
    # #2 : « shared » (3 moteurs sur 4) → signature partielle « plusieurs » ;
    # « lonely » (1 moteur) → « un seul ». Valeurs dérivées à la main.
    html = WordErrorsSection().render(_overlap_result(), SectionContext(lang="fr"))
    assert html is not None
    assert "recouvrement inter-moteurs" in html
    assert "plusieurs" in html and "shared" in html  # intersection partielle
    assert "un seul" in html and "lonely" in html  # propre à un moteur
    assert html == WordErrorsSection().render(_overlap_result(), SectionContext("fr"))


def test_no_payload_returns_none() -> None:
    section = WordErrorsSection()
    assert section.render(RunResult(manifest=_manifest()), SectionContext()) is None
