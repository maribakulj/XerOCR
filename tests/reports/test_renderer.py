"""Renderer : structure du document, déterminisme, no-orphan."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.renderer import (
    ReportRenderer,
    _label,
    _tab_layout,
    default_report_renderer,
)
from xerocr.reports.section import Html, SectionContext

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result() -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(
                pipeline="p",
                view="text",
                aggregate=(MetricScore(metric="cer", value=0.1, support=1),),
            ),
        ),
    )


def test_document_structure_and_determinism() -> None:
    renderer = default_report_renderer()
    html1 = renderer.render(_result())
    html2 = renderer.render(_result())
    assert html1 == html2  # octet-stable
    assert html1.startswith("<!DOCTYPE html>")
    assert "<title>" in html1
    assert "</html>" in html1
    # S4.a : le rapport porte le chrome au design (carte gris chaud + en-tête pilule)
    assert 'class="report-board"' in html1
    assert 'class="report-chrome"' in html1
    assert 'class="sec"' in html1
    # trame de points (halftone Xerox) en fond, via data: URI inline
    assert "data:image/svg+xml" in html1 and "fill-opacity" in html1
    # 3a : widget « comparer un run » (client-side) en pied de rapport.
    assert 'id="xerocr-compare-btn"' in html1
    # 3a : badge moteur (lettre + accent) devant le nom du moteur.
    assert 'class="eng-badge"' in html1
    # IA 4 onglets : barre de tabs + panneaux ARIA ; régions de section ancrées.
    assert 'class="report-tabs"' in html1
    assert 'role="tablist"' in html1
    assert 'role="tabpanel"' in html1
    assert 'id="panel-engines"' in html1  # onglet « Par moteur »
    assert 'id="r-by_engine"' in html1  # région ancrée (dans son panneau)
    assert 'aria-selected="true"' in html1  # 1er onglet actif
    # autonome : aucune ressource externe (ni @import, ni CDN https, ni <link>)
    assert "@import" not in html1
    assert "https://" not in html1
    assert "<link" not in html1


class _NeedsWer:
    name = "wer_section"
    requires = ("wer",)

    def render(self, result: RunResult, ctx: SectionContext) -> Html:
        return Html("<p>WER</p>")


class _Always:
    name = "always"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html:
        return Html("<p>ALWAYS</p>")


def test_no_orphan_skips_section_with_unmet_requires() -> None:
    html = ReportRenderer((_NeedsWer(), _Always())).render(_result())
    # On vérifie le **markup** rendu, pas une sous-chaîne nue : depuis que le
    # rapport incorpore ses polices (base64), "WER"/"ALWAYS" apparaissent par
    # hasard dans le data-URI. "<p>…</p>" ne peut pas (pas de "<" en base64).
    assert "<p>ALWAYS</p>" in html  # requires=() rendu
    assert "<p>WER</p>" not in html  # requires=("wer",) sauté (seul cer présent)


def test_tab_layout_groups_and_suppresses_bar_below_two() -> None:
    # 0-1 onglet actif → pas de barre (sections empilées) ; ≥ 2 → barre + panneaux.
    assert _tab_layout([], "fr") == ""
    one = _tab_layout([("overview", "<p>O</p>")], "fr")
    assert 'class="report-tabs"' not in one  # un seul onglet : barre inutile
    assert 'id="r-overview"' in one  # section quand même rendue (empilée)
    two = _tab_layout([("overview", "<p>O</p>"), ("by_engine", "<p>E</p>")], "fr")
    assert 'class="report-tabs"' in two and 'role="tablist"' in two
    assert 'id="panel-overview"' in two and 'id="panel-engines"' in two
    assert 'role="tabpanel"' in two
    assert two.count('aria-selected="true"') == 1  # exactement un onglet actif


def test_tab_labels_are_localized() -> None:
    rendered = [("overview", "<p>O</p>"), ("by_engine", "<p>E</p>")]
    assert "Par moteur" in _tab_layout(rendered, "fr")  # libellé FR (sans apostrophe)
    en = _tab_layout(rendered, "en")
    assert "Overview" in en and "Engines" in en


def test_unmapped_section_renders_after_panels() -> None:
    # glossary n'est pas mappé à un onglet → rendu hors onglets, après les panneaux.
    body = _tab_layout(
        [("overview", "<p>O</p>"), ("by_engine", "<p>E</p>"), ("glossary", "<p>G</p>")],
        "fr",
    )
    assert 'id="r-glossary"' in body
    assert body.index('id="r-glossary"') > body.index('id="panel-engines"')


def test_label_falls_back_to_raw_name() -> None:
    assert _label("by_engine") == "Par moteur"  # libellé FR connu
    assert _label("inconnue") == "inconnue"  # repli : nom brut
