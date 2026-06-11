"""Section **galerie** des documents (couche 7) — présentation visuelle au design.

≠ la table ``by_document`` (détail dense) : une **carte par document** avec un
**aperçu de page synthétique** (lignes monochromes sur ``--paper``, dans la charte
du rapport — pas de placeholder coloré, le travers évité), l'identifiant, et le
**CER de chaque moteur** via les badges A→E (le meilleur du document surligné en
``--fern``). 100 % données déjà présentes (``RunResult.documents``), **zéro image**,
autonome. Server-side, déterministe.
"""

from __future__ import annotations

from xerocr.evaluation.result import MetricScore, RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique


def _cer(scores: tuple[MetricScore, ...]) -> float | None:
    for score in scores:
        if score.metric == "cer":
            return score.value
    return None


def _row(pipeline: str, cer: float | None, index: int, *, best: bool) -> str:
    value = "—" if cer is None else f"{cer:.4f}"
    cls = "dc-row best" if best else "dc-row"
    return (
        f'<div class="{cls}">'
        f'<span class="eng-badge" style="--badge:{engine_accent(index)}">'
        f"{engine_letter(index)}</span>"
        f'<span class="dc-name">{escape(pipeline)}</span>'
        f'<span class="dc-cer">{value}</span></div>'
    )


def _card(
    doc_id: str,
    entries: list[tuple[str, float | None]],
    order: dict[str, int],
    idx: int,
) -> str:
    scored = [c for _, c in entries if c is not None]
    best = min(scored) if scored else None
    rows = "".join(
        _row(
            pipeline,
            cer,
            order.get(pipeline, 0),
            best=cer is not None and cer == best,
        )
        for pipeline, cer in sorted(
            entries, key=lambda e: (e[1] is None, e[1] or 0.0, e[0])
        )
    )
    # Carte = lien drill-in vers le détail du document (ancre #doc-<idx>).
    return (
        f'<a class="doc-card" href="#doc-{idx}">'
        '<div class="doc-preview" aria-hidden="true"></div>'
        f'<div class="dc-id">{escape(doc_id)}</div>'
        f'<div class="dc-rows">{rows}</div></a>'
    )


class DocumentGallerySection:
    """Galerie visuelle : une carte par document (aperçu synthétique + CER/badges)."""

    name = "documents_gallery"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.documents:
            return None
        view = ordered_unique(d.view for d in result.documents)[0]
        rows = [d for d in result.documents if d.view == view]
        # Ordre canonique des moteurs (badge stable, partagé avec les autres sections).
        order = engine_order(p.pipeline for p in result.pipelines) or engine_order(
            d.pipeline for d in rows
        )
        cards = "".join(
            _card(
                doc_id,
                [(d.pipeline, _cer(d.scores)) for d in rows if d.document_id == doc_id],
                order,
                idx,
            )
            for idx, doc_id in enumerate(ordered_unique(d.document_id for d in rows))
        )
        return Html(
            f"<h2>Galerie des documents (vue : {escape(view)})</h2>\n"
            '<p class="muted">Aperçu synthétique + CER par moteur '
            "(badge A→E ; meilleur du document surligné).</p>\n"
            f'<div class="doc-grid">{cards}</div>\n'
        )


__all__ = ["DocumentGallerySection"]
