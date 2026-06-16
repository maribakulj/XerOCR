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
    DocumentImageQuality,
    DocumentLines,
    DocumentLinesPayload,
    DocumentTexts,
    DocumentTextsPayload,
    ImageQualityPayload,
    WorstLine,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.text_diff import char_diff

_METRIC = "cer"
#: Paliers de qualité d'image (clés payload anglaises — contrat).
_TIER_FR = {"good": "bonne", "medium": "moyenne", "poor": "faible"}
_TIER_EN = {"good": "good", "medium": "medium", "poor": "poor"}


def _doc_image_quality(result: RunResult, doc_id: str) -> DocumentImageQuality | None:
    """Qualité d'image **de ce document** (scope corpus), ``None`` si non mesurée."""
    for analysis in result.analyses:
        payload = analysis.payload
        if isinstance(payload, ImageQualityPayload):
            for row in payload.documents:
                if row.document_id == doc_id:
                    return row
    return None


def _doc_lines(result: RunResult, doc_id: str) -> DocumentLines | None:
    """CER par ligne **de ce document** (scope corpus), ``None`` si non applicable."""
    for analysis in result.analyses:
        payload = analysis.payload
        if isinstance(payload, DocumentLinesPayload):
            for row in payload.documents:
                if row.document_id == doc_id:
                    return row
    return None


def _cer_bucket(value: float) -> str:
    """Palier de couleur d'une ligne : g(<5%) · m(<15%) · o(<30%) · b(≥30%)."""
    if value < 0.05:
        return "g"
    if value < 0.15:
        return "m"
    if value < 0.30:
        return "o"
    return "b"


def _line_heatmap(dl: DocumentLines, order: dict[str, int], lang: str) -> str:
    """Heatmap CER **par ligne** du document : une rangée de cases par moteur.

    Chaque case = une ligne GT, colorée par son CER (vert→rouge) ; **recentrée sur
    le doc** (où, dans la page, les erreurs se concentrent). Lecture seule."""
    rows = ""
    for pipeline, cers in dl.pipelines:
        idx = order.get(pipeline, 0)
        cells = "".join(
            f'<i class="lh-cell lh-{_cer_bucket(c)}" '
            f'title="ligne {i + 1} · CER {c * 100:.0f} %"></i>'
            for i, c in enumerate(cers)
        )
        rows += (
            '<div class="dd-lh-row"><span class="eng-badge" '
            f'style="--badge:{engine_accent(idx)}">{engine_letter(idx)}</span>'
            f'<span class="dd-name">{escape(pipeline)}</span>'
            f'<span class="dd-lh-cells">{cells}</span></div>'
        )
    title = localized(lang, "Erreurs par ligne (CER)", "Errors per line (CER)")
    legend = localized(
        lang,
        "vert &lt; 5 % · jaune &lt; 15 % · orange &lt; 30 % · rouge ≥ 30 %",
        "green &lt; 5% · yellow &lt; 15% · orange &lt; 30% · red ≥ 30%",
    )
    return (
        f'<div class="dd-lh"><div class="prof-chart-title">{title}</div>'
        f'<div class="dd-lh-rows">{rows}</div>'
        f'<div class="muted dd-iq-meta">{legend}</div></div>'
    )


def _iq_bar(label: str, value: float) -> str:
    """Mini-barre [0,1] d'une feature de qualité d'image (largeur = valeur)."""
    pct = max(0.0, min(1.0, value)) * 100
    return (
        f'<div class="dd-iq-row"><span class="dd-iq-lbl">{label}</span>'
        f'<span class="dd-iq-bar"><i style="width:{pct:.0f}%"></i></span>'
        f'<span class="dd-iq-val">{value:.2f}</span></div>'
    )


def _iq_block(iq: DocumentImageQuality, lang: str) -> str:
    """Bloc qualité d'image **du document** : barres mesurées + palier + inclinaison.

    Recentré sur CE doc (les features expliquent un CER élevé : image dégradée vs
    moteur faible). Lecture seule du payload — aucun recalcul (anti-hallucination)."""
    tier = (_TIER_FR if lang == "fr" else _TIER_EN).get(iq.tier, iq.tier)
    title = localized(lang, "Qualité de l'image", "Image quality")
    bars = (
        _iq_bar(localized(lang, "Netteté", "Sharpness"), iq.sharpness)
        + _iq_bar(localized(lang, "Contraste", "Contrast"), iq.contrast)
        + _iq_bar(localized(lang, "Propreté (1−bruit)", "Cleanliness (1−noise)"),
                  1.0 - iq.noise)
        + _iq_bar(localized(lang, "Score global", "Overall score"), iq.quality_score)
    )
    skew = localized(
        lang,
        f"palier : {tier} · inclinaison {iq.rotation_degrees:+.1f}°",
        f"tier: {tier} · skew {iq.rotation_degrees:+.1f}°",
    )
    return (
        f'<div class="dd-iq"><div class="prof-chart-title">{title}</div>'
        f'<div class="dd-iq-bars">{bars}</div>'
        f'<div class="muted dd-iq-meta">{skew}</div></div>'
    )


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
        # Fac-similé medium EN HAUT (pleine largeur, si résolu), puis CER par
        # moteur + diff côte à côte. Sans image : on saute le bloc (pas de vide).
        cer_title = localized(lang, "CER par moteur", "CER per engine")
        fac_block = ""
        if facsimile:
            fac_title = localized(lang, "Fac-similé", "Facsimile")
            fac_block = (
                f'<div class="dd-fac-top"><div class="prof-chart-title">{fac_title}'
                f'</div><img class="dd-fac-img" src="{escape(facsimile)}" alt="" '
                'loading="lazy" decoding="async"></div>'
            )
        # Graphiques recentrés sur CE doc : heatmap CER par ligne, puis qualité
        # d'image **en dernier** (demande utilisateur).
        dl = _doc_lines(result, doc_id)
        lh_block = _line_heatmap(dl, order, lang) if dl is not None else ""
        iq = _doc_image_quality(result, doc_id)
        iq_block = _iq_block(iq, lang) if iq is not None else ""
        # Ordre : fac-similé en haut → **texte** (diff GT/sortie) juste dessous →
        # CER par moteur → heatmap par ligne → qualité d'image **en bas**.
        body = (
            f"{fac_block}{diffs}"
            f'<div class="prof-chart-title">{cer_title}</div>'
            f'<div class="dd-cers">{cer_rows}</div>{lh_block}{iq_block}'
        )
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
                '<div class="dd-sbs">'
                f'<div class="dd-sbs-col"><div class="dd-diff-head mono">{ref_label}'
                f'</div><div class="diff">{ref_html}</div></div>'
                '<div class="dd-sbs-col"><div class="dd-diff-head mono">'
                f"{out_label} · {escape(p)}</div>"
                f'<div class="diff">{hyp_html}</div></div>'
                "</div></div>"
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
