"""Section détail document : panneaux **drill-in** par document (couche 7).

Révélé au clic d'une carte de galerie (ancre ``#doc-<idx>``). Affiche ce que la
donnée porte **réellement** : CER par moteur pour ce document + le **diff
caractère des pires lignes** de ce document (si présentes dans l'échantillon
``diagnostics``). Le fac-similé réel et le diff plein-texte arrivent avec les
tranches images (références dans ``RunResult``). Mécanique partagée avec le
profil moteur (``.drill-panel`` + ``report.js``) ; sans JS, ``:target``.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import (
    DiagnosticsPayload,
    DocumentTexts,
    DocumentTextsPayload,
    WorstLine,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape, localized
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


def _doc_texts(result: RunResult, view: str, doc_id: str) -> DocumentTexts | None:
    """Textes complets de ce document si le payload (top-N pires) les porte."""
    for analysis in result.analyses:
        payload = analysis.payload
        if analysis.view == view and isinstance(payload, DocumentTextsPayload):
            for dt in payload.documents:
                if dt.document_id == doc_id:
                    return dt
    return None


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
                result,
                view,
                doc_id,
                idx,
                doc_ids,
                order,
                ctx.facsimiles.get(doc_id),
                ctx.lang,
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
        lang: str,
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
        # Diff **pleine page** (texte complet + sélecteur de moteur) si le payload
        # textes porte ce doc (top-N pires) ; sinon **pires lignes** (toujours là).
        full = _doc_texts(result, view, doc_id)
        if full is not None and full.hypotheses:
            diffs = self._full_diff(full, order, lang)
        else:
            worst = _worst_lines(result, doc_id, view)
            diffs = ""
            if worst:
                items = "".join(self._diff_line(w, order, lang) for w in worst)
                worst_title = localized(
                    lang,
                    "Pires lignes (diff vérité-terrain ↔ sortie)",
                    "Worst lines (diff ground truth ↔ output)",
                )
                diffs = (
                    '<div class="dd-diffs"><div class="prof-chart-title">'
                    f"{worst_title}</div>{items}</div>"
                )
        # Fac-similé medium à gauche (si résolu), CER + diff à droite ; sinon
        # CER + diff en pleine largeur (dégradé propre, pas d'image vide).
        cer_title = localized(lang, "CER par moteur", "CER per engine")
        inner = (
            f'<div class="prof-chart-title">{cer_title}</div>'
            f'<div class="dd-cers">{cer_rows}</div>{diffs}'
        )
        if facsimile:
            fac_title = localized(lang, "Fac-similé", "Facsimile")
            body = (
                '<div class="dd-cols"><div class="dd-fac">'
                f'<div class="prof-chart-title">{fac_title}</div>'
                f'<img class="dd-fac-img" src="{escape(facsimile)}" alt="" '
                'loading="lazy" decoding="async"></div>'
                f'<div class="dd-right">{inner}</div></div>'
            )
        else:
            body = inner
        back = localized(lang, "← retour à la galerie", "← back to gallery")
        prev_label = localized(lang, "← précédent", "← previous")
        next_label = localized(lang, "suivant →", "next →")
        pos = localized(
            lang,
            f"document {idx + 1} sur {total}",
            f"document {idx + 1} of {total}",
        )
        return (
            f'<div class="drill-panel doc-detail" id="doc-{idx}" hidden '
            f'role="region" aria-label="{escape(doc_id)}">'
            '<div class="prof-head">'
            f'<a class="drill-back" href="#">{back}</a>'
            '<div class="prof-nav">'
            f'<a class="btn-sm" href="#doc-{prev_i}">{prev_label}</a>'
            f'<a class="btn-sm" href="#doc-{next_i}">{next_label}</a></div></div>'
            f'<div class="prof-title"><span>{escape(doc_id)}</span>'
            f'<span class="muted prof-pos">{pos}</span></div>'
            f"{body}</div>"
        )

    @staticmethod
    def _full_diff(texts: DocumentTexts, order: dict[str, int], lang: str) -> str:
        """Diff **pleine page** : vérité-terrain ↔ sortie, **sélecteur de moteur**.

        Un bloc par moteur (révélé par ``report.js`` ; sans JS, empilés). Le diff
        caractère est **échappé avant marquage** (anti-XSS, comme les pires lignes)."""
        hyps = texts.hypotheses
        tabs = "".join(
            f'<button type="button" class="dd-eng-btn{" on" if i == 0 else ""}" '
            f'data-engine="{escape(p)}"><span class="eng-badge" '
            f'style="--badge:{engine_accent(order.get(p, 0))}">'
            f"{engine_letter(order.get(p, 0))}</span>{escape(p)}</button>"
            for i, (p, _) in enumerate(hyps)
        )
        ref_label = localized(lang, "Vérité terrain", "Ground truth")
        out_label = localized(lang, "Sortie", "Output")
        blocks = ""
        for i, (p, hyp) in enumerate(hyps):
            ref_html, hyp_html = char_diff(texts.reference, hyp)
            hidden = "" if i == 0 else " hidden"
            blocks += (
                f'<div class="dd-fulldiff" data-engine="{escape(p)}"{hidden}>'
                f'<div class="dd-diff-head mono">{ref_label}</div>'
                f'<div class="diff">{ref_html}</div>'
                f'<div class="dd-diff-head mono">{out_label} · {escape(p)}</div>'
                f'<div class="diff">{hyp_html}</div></div>'
            )
        full_title = localized(
            lang,
            "Diff vérité-terrain ↔ sortie (page complète)",
            "Diff ground truth ↔ output (full page)",
        )
        return (
            f'<div class="dd-fullwrap"><div class="prof-chart-title">{full_title}'
            "</div>"
            f'<div class="dd-engine-tabs segmented" role="tablist">{tabs}</div>'
            f"{blocks}</div>"
        )

    @staticmethod
    def _diff_line(w: WorstLine, order: dict[str, int], lang: str) -> str:
        ref_html, hyp_html = char_diff(w.reference, w.hypothesis)
        idx = order.get(w.pipeline, 0)
        head = localized(
            lang,
            f"{escape(w.pipeline)} · ligne {w.line_index} · CER {w.cer * 100:.0f} %",
            f"{escape(w.pipeline)} · line {w.line_index} · CER {w.cer * 100:.0f} %",
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
