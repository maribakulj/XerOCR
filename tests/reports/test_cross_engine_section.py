"""Section cross_engine : clé parsée en colonnes + verdict, ``None`` si absent.

Étendue 4e.1 : blocs ``inter_engine`` (complémentarité oracle + divergence JS),
avec la borne bag-of-words **documentée dans la prose** (anti-surinterprétation).
"""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    ComplementarityDocument,
    EngineTokenRecall,
    InferencePayload,
    InterEngineComplementarity,
    InterEngineDivergence,
    InterEnginePayload,
    PipelineInterval,
    PipelineRank,
    TaxonomyDivergencePair,
)
from xerocr.evaluation.result import MetricScore, RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.cross_engine import CrossEngineSection

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


def _result(metric: str, value: float | None) -> RunResult:
    return RunResult(
        manifest=_manifest(),
        cross_engine=(MetricScore(metric=metric, value=value, support=10),),
    )


def test_significant_verdict_and_parsed_columns() -> None:
    html = CrossEngineSection().render(
        _result("text:cer:significance_p", 0.03), SectionContext()
    )
    assert html is not None
    assert "Significativité" in html
    # clé éclatée en colonnes Vue / Métrique
    assert ">text<" in html and ">cer<" in html
    assert "0.0300" in html
    assert "significatif" in html  # p=0,03 < 0,05


def test_non_significant_verdict() -> None:
    html = CrossEngineSection().render(
        _result("text:cer:significance_p", 0.20), SectionContext()
    )
    assert html is not None
    assert "non sig." in html  # p=0,20 ≥ 0,05


def test_none_value_rendered_as_dash() -> None:
    html = CrossEngineSection().render(_result("x", None), SectionContext())
    assert html is not None
    assert "—" in html


def test_empty_cross_engine_returns_none() -> None:
    section = CrossEngineSection()
    assert section.render(RunResult(manifest=_manifest()), SectionContext()) is None


def test_inference_block_renders_ranks_cd_and_intervals() -> None:
    payload = InferencePayload(
        metric="cer",
        alpha=0.05,
        n_documents=8,
        critical_distance=1.1715,
        q_alpha=2.343,
        mean_ranks=(
            PipelineRank(pipeline="alpha", mean_rank=1.375),
            PipelineRank(pipeline="beta", mean_rank=3.0),
        ),
        tied_groups=(("alpha",), ("beta",)),
        intervals=(
            PipelineInterval(
                pipeline="alpha", mean=0.1062, lower=0.095, upper=0.1162,
                n_documents=8,
            ),
        ),
    )
    result = RunResult(
        manifest=_manifest(),
        cross_engine=(
            MetricScore(metric="text:cer:significance_p", value=0.01, support=8),
        ),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )
    html = CrossEngineSection().render(result, SectionContext())
    assert html is not None
    assert "CD = 1.1715" in html
    assert "rang moyen" in html
    assert "[0.0950 ; 0.1162]" in html
    assert "{alpha}" in html and "{beta}" in html
    # Déterminisme bit-à-bit du rendu.
    assert html == CrossEngineSection().render(result, SectionContext())


def test_two_pipeline_inference_block_points_to_wilcoxon() -> None:
    payload = InferencePayload(
        metric="cer",
        alpha=0.05,
        n_documents=8,
        mean_ranks=(
            PipelineRank(pipeline="alpha", mean_rank=1.0),
            PipelineRank(pipeline="beta", mean_rank=2.0),
        ),
    )
    result = RunResult(
        manifest=_manifest(),
        cross_engine=(
            MetricScore(metric="text:cer:significance_p", value=0.02, support=8),
        ),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )
    html = CrossEngineSection().render(result, SectionContext())
    assert html is not None
    assert "pas de post-hoc" in html


def _inter_engine_result() -> RunResult:
    """Témoin : payload ``inter_engine`` seul (aucun scalaire cross_engine)."""
    payload = InterEnginePayload(
        complementarity=InterEngineComplementarity(
            n_documents=3,
            n_reference_tokens=120,
            oracle_recall=0.95,
            best_single_recall=0.9,
            best_engine="alpha",
            absolute_gap=0.05,
            relative_gap=0.5,
            per_engine_recall=(
                EngineTokenRecall(pipeline="alpha", recall=0.9),
                EngineTokenRecall(pipeline="beta", recall=0.85),
            ),
            per_document=(
                ComplementarityDocument(
                    document_id="d2",
                    oracle_recall=0.9,
                    best_single_recall=0.7,
                    absolute_gap=0.2,
                ),
            ),
        ),
        taxonomy_divergence=InterEngineDivergence(
            pairs=(
                TaxonomyDivergencePair(a="alpha", b="beta", divergence=0.1887),
            ),
            max_pair=TaxonomyDivergencePair(a="alpha", b="beta", divergence=0.1887),
        ),
    )
    return RunResult(
        manifest=_manifest(),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def test_inter_engine_blocks_render_with_documented_bound() -> None:
    # Le payload seul suffit (pas de scalaire cross_engine requis) ; la borne
    # bag-of-words est documentée dans la prose (anti-surinterprétation).
    html = CrossEngineSection().render(_inter_engine_result(), SectionContext())
    assert html is not None
    assert "complémentarité" in html
    assert "oracle" in html
    assert "Borne supérieure" in html and "ordre est ignoré" in html
    assert "95.0%" in html and "90.0%" in html  # oracle + meilleur seul
    assert "alpha" in html and "beta" in html
    assert "d2" in html and "20.0%" in html  # document au plus fort écart
    assert "Jensen-Shannon" in html
    assert "0.1887" in html  # divergence de la paire (et de max_pair)
    # Déterminisme bit-à-bit du rendu.
    assert html == CrossEngineSection().render(_inter_engine_result(), SectionContext())


def test_renders_english_labels() -> None:
    # Mêmes fixtures, contexte EN : libellés anglais présents, FR absents.
    result = _result("text:cer:significance_p", 0.03)
    html = CrossEngineSection().render(result, SectionContext(lang="en"))
    assert html is not None
    assert "Inter-engine significance" in html and "Significativité" not in html
    assert "significant" in html and "significatif" not in html
    assert ">View<" in html and ">Vue<" not in html
    # Le bloc inter-moteurs (complémentarité + divergence) bascule aussi en EN.
    inter = CrossEngineSection().render(
        _inter_engine_result(), SectionContext(lang="en")
    )
    assert inter is not None
    assert "engine complementarity" in inter and "complémentarité" not in inter
    assert "Upper bound" in inter and "Borne supérieure" not in inter


def test_divergence_without_max_pair_says_identical_profiles() -> None:
    payload = InterEnginePayload(
        taxonomy_divergence=InterEngineDivergence(
            pairs=(TaxonomyDivergencePair(a="alpha", b="beta", divergence=0.0),),
            max_pair=None,
        ),
    )
    result = RunResult(
        manifest=_manifest(),
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )
    html = CrossEngineSection().render(result, SectionContext())
    assert html is not None
    assert "identiques" in html  # pas de « paire la plus divergente » inventée
    assert "0.0000" in html
