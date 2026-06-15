"""Section composition du corpus : répartition par strate (si présentes)."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import (
    MetricScore,
    RunDocumentResult,
    RunResult,
)
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.corpus_composition import CorpusCompositionSection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _doc(doc_id: str, stratum: str | None) -> RunDocumentResult:
    return RunDocumentResult(
        document_id=doc_id, pipeline="tess", view="text", stratum=stratum,
        scores=(MetricScore(metric="cer", value=0.1, support=1),),
    )


def _result(*documents: RunDocumentResult) -> RunResult:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=len(documents),
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    return RunResult(manifest=manifest, documents=documents)


def test_renders_strata_counts_and_shares() -> None:
    html = CorpusCompositionSection().render(
        _result(
            _doc("a", "manuscrit"), _doc("b", "manuscrit"),
            _doc("c", "manuscrit"), _doc("d", "imprimé"), _doc("e", "imprimé"),
        ),
        SectionContext(),
    )
    assert html is not None
    assert "Composition du corpus" in html
    assert "manuscrit" in html and "imprimé" in html
    assert "n = 3" in html and "n = 2" in html  # effectifs réels
    assert "60%" in html and "40%" in html  # parts (3/5, 2/5)
    # ordre déterministe : strate majoritaire d'abord
    assert html.index("manuscrit") < html.index("imprimé")


def test_renders_english_labels() -> None:
    html = CorpusCompositionSection().render(
        _result(_doc("a", "manuscrit"), _doc("b", "imprimé")),
        SectionContext(lang="en"),
    )
    assert html is not None
    assert "Corpus composition" in html and "strata" in html
    assert "Composition du corpus" not in html


def test_none_when_no_stratum() -> None:
    # Aucune strate → pas de carte (jamais de strate inventée).
    html = CorpusCompositionSection().render(
        _result(_doc("a", None), _doc("b", None)), SectionContext()
    )
    assert html is None


def test_none_without_documents() -> None:
    manifest = RunManifest(
        run_id="r", corpus_name="demo", n_documents=0,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    assert CorpusCompositionSection().render(
        RunResult(manifest=manifest), SectionContext()
    ) is None
