"""Section fidélité textuelle : rappel rare + table de modernisation."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    ModernizedToken,
    ModernizedVariant,
    PipelineTextualFidelity,
    TextualFidelityPayload,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.textual_fidelity import TextualFidelitySection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result(payload: TextualFidelityPayload) -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def _payload() -> TextualFidelityPayload:
    row = PipelineTextualFidelity(
        pipeline="eng",
        n_rare_reference=6,
        n_rare_recalled=5,
        rare_recall=5 / 6,
        missed=("louis",),
        modernization=(
            ModernizedToken(
                token="maistre",
                n_total=4,
                n_modernized=3,
                rate=0.75,
                variants=(ModernizedVariant(form="maître", count=3),),
            ),
        ),
    )
    return TextualFidelityPayload(max_freq=2, pipelines=(row,))


def test_renders_rare_and_modernization() -> None:
    html = TextualFidelitySection().render(_result(_payload()), SectionContext())
    assert html is not None
    assert "Fidélité textuelle" in html
    assert "5/6" in html and "83.3%" in html  # rappel rare
    assert "louis" in html  # échantillon manqué
    assert "maistre" in html and "maître ×3" in html  # modernisation + variante
    assert "75.0%" in html


def test_returns_none_without_payload() -> None:
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=0,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    empty = RunResult(manifest=manifest)
    assert TextualFidelitySection().render(empty, SectionContext()) is None


def test_modernization_table_absent_when_no_rewrite() -> None:
    row = PipelineTextualFidelity(
        pipeline="eng", n_rare_reference=2, n_rare_recalled=2, rare_recall=1.0
    )
    html = TextualFidelitySection().render(
        _result(TextualFidelityPayload(max_freq=2, pipelines=(row,))), SectionContext()
    )
    assert html is not None
    assert "rappel des tokens rares" in html
    assert "modernisation lexicale" not in html  # pas de réécriture → pas de table
