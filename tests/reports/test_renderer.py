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
    assert 'class="r-block sec"' in html1  # chaque section = sa propre carte .sec
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
    # _tab_layout → (barre_onglets, corps_panneaux). La barre part dans le chrome.
    # 0-1 onglet actif → pas de barre (sections empilées) ; ≥ 2 → barre + panneaux.
    assert _tab_layout([], "fr") == ("", "")
    tabs_one, body_one = _tab_layout([("overview", "<p>O</p>")], "fr")
    assert tabs_one == ""  # un seul onglet : barre inutile
    assert 'id="r-overview"' in body_one  # section quand même rendue (empilée)
    rendered = [("overview", "<p>O</p>"), ("by_engine", "<p>E</p>")]
    tabs, body = _tab_layout(rendered, "fr")
    assert 'class="report-tabs"' in tabs and 'role="tablist"' in tabs
    assert 'id="panel-overview"' in body and 'id="panel-engines"' in body
    assert 'role="tabpanel"' in body
    assert tabs.count('aria-selected="true"') == 1  # exactement un onglet actif


def test_tab_labels_are_localized() -> None:
    rendered = [("overview", "<p>O</p>"), ("by_engine", "<p>E</p>")]
    tabs_fr, _ = _tab_layout(rendered, "fr")
    assert "Par moteur" in tabs_fr  # libellé FR (sans apostrophe)
    tabs_en, _ = _tab_layout(rendered, "en")
    assert "Overview" in tabs_en and "Engines" in tabs_en


def test_unmapped_section_renders_after_panels() -> None:
    # glossary n'est pas mappé à un onglet → rendu hors onglets, après les panneaux.
    _, body = _tab_layout(
        [("overview", "<p>O</p>"), ("by_engine", "<p>E</p>"), ("glossary", "<p>G</p>")],
        "fr",
    )
    assert 'id="r-glossary"' in body
    assert body.index('id="r-glossary"') > body.index('id="panel-engines"')


def test_label_falls_back_to_raw_name() -> None:
    assert _label("by_engine") == "Par moteur"  # libellé FR connu
    assert _label("inconnue") == "inconnue"  # repli : nom brut


def test_chrome_meta_and_exports_present() -> None:
    # Chrome : méta de run (docs/moteurs) + exports CSV/JSON en data: (offline).
    html = default_report_renderer().render(_result())
    assert 'class="chrome-meta"' in html
    assert "docs" in html and "moteurs" in html  # libellés méta FR
    assert 'download="r.csv"' in html  # run_id="r"
    assert 'href="data:text/csv' in html
    assert 'download="r.json"' in html
    assert 'href="data:application/json' in html
    # autonomie : les exports sont des data: URI, aucune ressource réseau
    assert "https://" not in html


def test_each_section_is_its_own_card() -> None:
    # Plus de méga-carte : chaque section porte sa propre carte .sec ancrée.
    html = default_report_renderer().render(_result())
    assert 'class="r-block sec"' in html
    # le corps n'est plus enveloppé dans une <section class="sec"> unique
    assert '<main class="report-main"><section class="sec">' not in html
