"""Section détail document : panneaux **drill-in** par document (couche 7).

Révélé au clic d'une carte de galerie (ancre ``#doc-<idx>``). Affiche ce que la
donnée porte **réellement** : CER par moteur pour ce document + le **diff
caractère des pires lignes** de ce document (si présentes dans l'échantillon
``diagnostics``). Le fac-similé réel et le diff plein-texte arrivent avec les
tranches images (références dans ``RunResult``). Mécanique partagée avec le
profil moteur (``.drill-panel`` + ``report.js``) ; sans JS, ``:target``.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import DiagnosticsPayload, WorstLine
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.text_diff import char_diff

_METRIC = "cer"


def _doc_cer(result: RunResult, doc_id: str, view: str) -> list[tuple[str, float]]:
    """(pipeline, CER) du document, pour la vue."""
    out: list[tuple[str, float]] = []
    for d in result.documents:
        if d.document_id == doc_id and d.view == view:
            for s in d.scores:
                if s.metric == _METRIC and s.value is not None:
                    out.append((d.pipeline, s.value))
    return out


def _worst_lines(result: RunResult, doc_id: str, view: str) -> list[WorstLine]:
    """Pires lignes de ce document présentes dans l'échantillon diagnostics."""
    lines: list[WorstLine] = []
    for analysis in result.analyses:
        payload = analysis.payload
        if analysis.view == view and isinstance(payload, DiagnosticsPayload):
            lines += [w for w in payload.worst_lines if w.document_id == doc_id]
    return lines


class DocumentDetailSection:
    """Panneaux détail par document (CER/moteur + diff des pires lignes)."""

    name = "document_details"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.documents:
            return None
        view = ordered_unique(d.view for d in result.documents)[0]
        rows = [d for d in result.documents if d.view == view]
        doc_ids = list(ordered_unique(d.document_id for d in rows))
        order = engine_order(p.pipeline for p in result.pipelines) or engine_order(
            d.pipeline for d in rows
        )
        panels = "".join(
            self._panel(
                result, view, doc_id, idx, doc_ids, order, ctx.facsimiles.get(doc_id)
            )
            for idx, doc_id in enumerate(doc_ids)
        )
        return Html(f'<div class="doc-details">{panels}</div>')

    def _panel(
        self,
        result: RunResult,
        view: str,
        doc_id: str,
        idx: int,
        doc_ids: list[str],
        order: dict[str, int],
        facsimile: str | None,
    ) -> str:
        total = len(doc_ids)
        prev_i = (idx - 1) % total
        next_i = (idx + 1) % total
        cers = sorted(_doc_cer(result, doc_id, view), key=lambda e: (e[1], e[0]))
        best = cers[0][1] if cers else None
        cer_rows = "".join(
            f'<div class="dd-row{" best" if c == best else ""}">'
            f'<span class="eng-badge" style="--badge:{engine_accent(order.get(p, 0))}">'
            f"{engine_letter(order.get(p, 0))}</span>"
            f'<span class="dd-name">{escape(p)}</span>'
            f'<span class="dd-cer">{c * 100:.1f} %</span></div>'
            for p, c in cers
        )
        worst = _worst_lines(result, doc_id, view)
        diffs = ""
        if worst:
            items = "".join(self._diff_line(w, order) for w in worst)
            diffs = (
                '<div class="dd-diffs"><div class="prof-chart-title">Pires lignes '
                f"(diff vérité-terrain ↔ sortie)</div>{items}</div>"
            )
        # Fac-similé medium à gauche (si résolu), CER + diff à droite ; sinon
        # CER + diff en pleine largeur (dégradé propre, pas d'image vide).
        inner = (
            '<div class="prof-chart-title">CER par moteur</div>'
            f'<div class="dd-cers">{cer_rows}</div>{diffs}'
        )
        if facsimile:
            body = (
                '<div class="dd-cols"><div class="dd-fac">'
                '<div class="prof-chart-title">Fac-similé</div>'
                f'<img class="dd-fac-img" src="{escape(facsimile)}" alt="" '
                'loading="lazy" decoding="async"></div>'
                f'<div class="dd-right">{inner}</div></div>'
            )
        else:
            body = inner
        return (
            f'<div class="drill-panel doc-detail" id="doc-{idx}" hidden '
            f'role="region" aria-label="{escape(doc_id)}">'
            '<div class="prof-head">'
            '<a class="drill-back" href="#">← retour à la galerie</a>'
            '<div class="prof-nav">'
            f'<a class="btn-sm" href="#doc-{prev_i}">← précédent</a>'
            f'<a class="btn-sm" href="#doc-{next_i}">suivant →</a></div></div>'
            f'<div class="prof-title"><span>{escape(doc_id)}</span>'
            f'<span class="muted prof-pos">document {idx + 1} sur {total}</span></div>'
            f"{body}</div>"
        )

    @staticmethod
    def _diff_line(w: WorstLine, order: dict[str, int]) -> str:
        ref_html, hyp_html = char_diff(w.reference, w.hypothesis)
        idx = order.get(w.pipeline, 0)
        head = (
            f"{escape(w.pipeline)} · ligne {w.line_index} · CER {w.cer * 100:.0f} %"
        )
        return (
            '<div class="dd-diff">'
            f'<div class="dd-diff-head mono"><span class="eng-badge" '
            f'style="--badge:{engine_accent(idx)}">{engine_letter(idx)}</span>'
            f"{head}</div>"
            f'<div class="diff">{ref_html}</div>'
            f'<div class="diff">{hyp_html}</div></div>'
        )


__all__ = ["DocumentDetailSection"]
