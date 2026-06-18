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
    DocumentHallucination,
    DocumentHallucinationPayload,
    DocumentImageQuality,
    DocumentLines,
    DocumentLinesPayload,
    DocumentTexts,
    DocumentTextsPayload,
    ImageQualityPayload,
    WorstLine,
)
from xerocr.evaluation.lines import gini, percentile
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


_PCTS = (("p50", 50.0), ("p75", 75.0), ("p90", 90.0), ("p95", 95.0), ("p99", 99.0))


def _line_distribution(dl: DocumentLines, order: dict[str, int], lang: str) -> str:
    """Distribution des erreurs **par ligne** du document, par moteur.

    Trois lectures complémentaires, dérivées des CER de ligne (fonctions pures
    partagées ``percentile``/``gini``) : (1) **carte thermique de position** (une
    barre = une ligne, gauche→droite = haut→bas, hauteur ∝ CER) → *où* ; (2)
    **percentiles CER** (p50→p99) → *l'étalement* (un p50 bas + p99 haut = quelques
    lignes catastrophiques que le CER moyen masque) ; (3) **badges** (CER moyen,
    Gini de concentration, n lignes, % de lignes au-dessus de seuils). Lecture seule."""
    start = localized(lang, "début", "start")
    end = localized(lang, "fin", "end")
    heat_l = localized(lang, "carte thermique (position)", "heatmap (position)")
    pct_l = localized(lang, "percentiles CER", "CER percentiles")
    lines_l = localized(lang, "lignes", "lines")
    rows = ""
    for pipeline, cers in dl.pipelines:
        idx = order.get(pipeline, 0)
        n = len(cers)
        ordered = sorted(cers)
        mean_cer = sum(cers) / n
        chips = (
            f'<span class="chip">CER {mean_cer * 100:.1f} %</span>'
            f'<span class="chip">Gini {gini(cers):.2f}</span>'
            f'<span class="chip">{n} {lines_l}</span>'
        )
        for thr in (0.30, 0.50, 1.0):
            rate = sum(1 for c in cers if c >= thr) / n
            chips += (
                f'<span class="chip">{rate * 100:.0f} % {lines_l} '
                f"CER≥{thr * 100:.0f} %</span>"
            )
        bars = "".join(
            f'<i class="dd-lh-bar lh-{_cer_bucket(c)}" '
            f'style="height:{4 + round(36 * min(c, 1.0))}px" '
            f'title="ligne {i + 1} · CER {c * 100:.0f} %"></i>'
            for i, c in enumerate(cers)
        )
        pcts = "".join(
            f'<div class="dd-pct-row"><span class="dd-pct-lbl">{label}</span>'
            f'<span class="track"><i class="lh-{_cer_bucket(v)}" '
            f'style="width:{min(100.0, v * 100):.0f}%"></i></span>'
            f'<span class="dd-pct-val">{v * 100:.1f} %</span></div>'
            for label, v in (
                (lbl, percentile(ordered, q)) for lbl, q in _PCTS
            )
        )
        rows += (
            '<div class="dd-ld-row"><div class="dd-ld-head"><span class="eng-badge" '
            f'style="--badge:{engine_accent(idx)}">{engine_letter(idx)}</span>'
            f'<span class="dd-name">{escape(pipeline)}</span>{chips}</div>'
            '<div class="dd-ld-grid"><div class="dd-ld-cell">'
            f'<div class="dd-ld-sub">{heat_l}</div>'
            f'<div class="dd-lh-bars">{bars}</div>'
            f'<div class="dd-lh-axis"><span>{start}</span><span>{end}</span></div>'
            '</div><div class="dd-ld-cell">'
            f'<div class="dd-ld-sub">{pct_l}</div>{pcts}</div></div></div>'
        )
    title = localized(
        lang, "Distribution des erreurs par ligne", "Per-line error distribution"
    )
    return (
        f'<div class="dd-lh"><div class="drill-caption">{title}</div>'
        f'<div class="dd-ld-rows">{rows}</div></div>'
    )


def _doc_hallucination(
    result: RunResult, doc_id: str
) -> DocumentHallucination | None:
    """Analyse d'hallucination **de ce document** (scope corpus), ``None`` si absent."""
    for analysis in result.analyses:
        payload = analysis.payload
        if isinstance(payload, DocumentHallucinationPayload):
            for row in payload.documents:
                if row.document_id == doc_id:
                    return row
    return None


def _hallucination_block(
    dh: DocumentHallucination, order: dict[str, int], lang: str
) -> str:
    """Analyse d'hallucination du document : par moteur, indicateurs + blocs inventés.

    Le plus parlant quand un moteur **invente** du texte (mauvaise langue, VLM/LLM) :
    ancrage faible / insertion nette élevée + les **blocs hallucinés affichés**.
    Lecture seule du payload (aucun recalcul)."""
    title = localized(lang, "Analyse des hallucinations", "Hallucination analysis")
    flag = localized(lang, "⚠ hallucination détectée", "⚠ hallucination detected")
    anchor_l = localized(lang, "Ancrage", "Anchoring")
    ratio_l = localized(lang, "Ratio longueur", "Length ratio")
    netins_l = localized(lang, "Insertion nette", "Net insertion")
    words_l = localized(lang, "mots GT / sortie", "GT / output words")
    blocks_l = localized(
        lang, "Blocs sans ancrage dans le GT", "Blocks unanchored in GT"
    )
    rows = ""
    for ph in dh.pipelines:
        idx = order.get(ph.pipeline, 0)
        badge = (
            f'<span class="eng-badge" style="--badge:{engine_accent(idx)}">'
            f"{engine_letter(idx)}</span>"
        )
        chips = (
            f'<span class="chip">{anchor_l} {ph.anchor_score * 100:.0f} %</span>'
            f'<span class="chip">{ratio_l} {ph.length_ratio:.2f}</span>'
            f'<span class="chip">{netins_l} {ph.net_insertion_rate * 100:.0f} %'
            "</span>"
            f'<span class="chip">{ph.gt_words} / {ph.hyp_words} {words_l}</span>'
        )
        warn = f'<span class="dd-hl-flag">{flag}</span>' if ph.is_hallucinating else ""
        blocks = ""
        if ph.blocks:
            items = "".join(
                f'<div class="dd-hl-block"><span class="muted">'
                f"mots {b.start_token}–{b.end_token}</span> {escape(b.text)}</div>"
                for b in ph.blocks
            )
            blocks = (
                f'<div class="dd-hl-blocks"><div class="muted">{blocks_l} :</div>'
                f"{items}</div>"
            )
        rows += (
            f'<div class="dd-hl-row"><div class="dd-hl-head">{badge}'
            f'<span class="dd-name">{escape(ph.pipeline)}</span>{warn}</div>'
            f'<div class="chips">{chips}</div>{blocks}</div>'
        )
    return (
        f'<div class="dd-hl"><div class="drill-caption">{title}</div>{rows}</div>'
    )


def _iq_bar(label: str, value: float) -> str:
    """Mini-barre [0,1] d'une feature de qualité d'image (largeur = valeur)."""
    pct = max(0.0, min(1.0, value)) * 100
    return (
        f'<div class="dd-iq-row"><span class="dd-iq-lbl">{label}</span>'
        f'<span class="track"><i style="width:{pct:.0f}%;background:var(--g-300)">'
        "</i></span>"
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
        f'<div class="dd-iq"><div class="drill-caption">{title}</div>'
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
                    '<div class="dd-diffs"><div class="drill-caption">'
                    f"{worst_title}</div>{items}</div>"
                )
        # Fac-similé medium EN HAUT (pleine largeur, si résolu), puis CER par
        # moteur + diff côte à côte. Sans image : on saute le bloc (pas de vide).
        cer_title = localized(lang, "CER par moteur", "CER per engine")
        fac_block = ""
        if facsimile:
            fac_title = localized(lang, "Fac-similé", "Facsimile")
            zin = localized(lang, "Zoom avant", "Zoom in")
            zout = localized(lang, "Zoom arrière", "Zoom out")
            zreset = localized(lang, "Réinitialiser le zoom", "Reset zoom")
            fac_block = (
                f'<div class="dd-fac-top"><div class="drill-caption">{fac_title}'
                '</div><div class="dd-fac-zoom">'
                f'<img class="dd-fac-img" src="{escape(facsimile)}" alt="" '
                'loading="lazy" decoding="async">'
                '<div class="dd-zoom-ctl">'
                f'<button type="button" data-zoom="out" aria-label="{zout}">−</button>'
                f'<button type="button" data-zoom="reset" aria-label="{zreset}">⤢'
                "</button>"
                f'<button type="button" data-zoom="in" aria-label="{zin}">+</button>'
                "</div></div></div>"
            )
        # Graphiques recentrés sur CE doc : heatmap CER par ligne, puis qualité
        # d'image **en dernier** (demande utilisateur).
        dl = _doc_lines(result, doc_id)
        lh_block = _line_distribution(dl, order, lang) if dl is not None else ""
        dh = _doc_hallucination(result, doc_id)
        hl_block = _hallucination_block(dh, order, lang) if dh is not None else ""
        iq = _doc_image_quality(result, doc_id)
        iq_block = _iq_block(iq, lang) if iq is not None else ""
        # Haut : fac-similé **en bandeau étroit centré au-dessus**, puis le diff
        # GT/sortie **côte à côte sur toute la largeur** en dessous — chaque
        # colonne de texte a ~2× plus de place (sauts de ligne propres sur petit
        # écran, et tient même pour de longues pages multi-colonnes). Sans image :
        # le diff seul. Puis CER → heatmap ligne → hallucinations → qualité image.
        top = f"{fac_block}{diffs}"
        body = (
            f"{top}"
            f'<div class="drill-caption">{cer_title}</div>'
            f'<div class="dd-cers">{cer_rows}</div>{lh_block}{hl_block}{iq_block}'
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
            '<div class="drill-head">'
            f'<a class="drill-back" href="#">{back}</a>'
            '<div class="drill-nav">'
            f'<a class="btn-sm" href="#doc-{prev_i}">{prev_label}</a>'
            f'<a class="btn-sm" href="#doc-{next_i}">{next_label}</a></div></div>'
            f'<div class="drill-title"><span>{escape(doc_id)}</span>'
            f'<span class="muted drill-pos">{pos}</span></div>'
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
            f'<div class="dd-fullwrap"><div class="drill-caption">{full_title}'
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
